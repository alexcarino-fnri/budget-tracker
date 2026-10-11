from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from decimal import Decimal
from wallets.models import Account
from transactions.models import Transaction

class TransactionsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='Password123!')
        self.user_b = User.objects.create_user(username='user_b', password='Password123!')

        self.acc_a1 = Account.objects.create(user=self.user_a, name='Wallet A1')
        self.acc_a2 = Account.objects.create(user=self.user_a, name='Wallet A2')
        self.acc_b = Account.objects.create(user=self.user_b, name='Wallet B')

        self.tx_a = Transaction.objects.create(
            user=self.user_a,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('50.00'),
            account=self.acc_a1,
            description='Groceries user A'
        )
        self.tx_b = Transaction.objects.create(
            user=self.user_b,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('100.00'),
            account=self.acc_b,
            description='Secret expense user B'
        )

    def test_amount_must_be_positive(self):
        tx = Transaction(
            user=self.user_a,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('-10.00'),
            account=self.acc_a1,
            description='Negative Test'
        )
        with self.assertRaises(ValidationError):
            tx.full_clean()

    def test_transfer_validation(self):
        # Transfer without to_account should fail validation
        tx_no_dest = Transaction(
            user=self.user_a,
            transaction_type=Transaction.TYPE_TRANSFER,
            amount=Decimal('100.00'),
            account=self.acc_a1,
            description='Invalid transfer'
        )
        with self.assertRaises(ValidationError):
            tx_no_dest.clean()

        # Transfer to same account should fail
        tx_same_dest = Transaction(
            user=self.user_a,
            transaction_type=Transaction.TYPE_TRANSFER,
            amount=Decimal('100.00'),
            account=self.acc_a1,
            to_account=self.acc_a1,
            description='Same account transfer'
        )
        with self.assertRaises(ValidationError):
            tx_same_dest.clean()

    def test_permission_scoping_users_cannot_access_each_others_transactions(self):
        client = Client()
        client.login(username='user_a', password='Password123!')

        # User A views transaction list
        response = client.get(reverse('transactions:list'))
        self.assertContains(response, 'Groceries user A')
        self.assertNotContains(response, 'Secret expense user B')

        # User A attempts to edit user B's transaction
        response = client.get(reverse('transactions:update', kwargs={'pk': self.tx_b.pk}))
        self.assertEqual(response.status_code, 404)

        # User A attempts to delete user B's transaction
        response = client.post(reverse('transactions:delete', kwargs={'pk': self.tx_b.pk}))
        self.assertEqual(response.status_code, 404)

    def test_ocr_parser_extracts_details_and_detects_debt(self):
        from transactions.ocr_service import parse_receipt_text_to_data
        from debts.models import Debt
        from wallets.models import Account
        from datetime import date

        gcash_account = Account.objects.create(user=self.user_a, name='GCash Wallet', account_type='E_WALLET')
        bdo_loan = Debt.objects.create(
            user=self.user_a,
            debt_type=Debt.TYPE_OWED_BY_ME,
            title='BDO Auto Loan',
            creditor_or_debtor='BDO Unibank',
            principal=Decimal('50000.00'),
            due_date=date(2026, 12, 1)
        )

        receipt_text = """
        GCash Payment Receipt
        Reference No: 900213847291
        Date: 2026-10-10
        Merchant: BDO Auto Loan Repayment
        Total Amount Paid: PHP 4,500.00
        Status: SUCCESSFUL
        Paid using: GCash
        """

        parsed = parse_receipt_text_to_data(receipt_text, self.user_a)

        self.assertEqual(parsed['amount'], '4500.00')
        self.assertEqual(parsed['account_id'], gcash_account.id)
        self.assertTrue(parsed['is_debt_payment'])
        self.assertEqual(parsed['debt_id'], bdo_loan.id)
        self.assertEqual(parsed['debt_title'], 'BDO Auto Loan')

    def test_process_scanned_receipt_creates_transaction_and_debt_payment(self):
        from debts.models import Debt, DebtPayment
        from datetime import date

        client = Client()
        client.login(username='user_a', password='Password123!')

        debt = Debt.objects.create(
            user=self.user_a,
            debt_type=Debt.TYPE_OWED_BY_ME,
            title='Laptop Amortization',
            creditor_or_debtor='Home Credit',
            principal=Decimal('30000.00'),
            due_date=date(2026, 12, 1)
        )

        response = client.post(reverse('transactions:process_scanned_receipt'), {
            'amount': '2500.00',
            'date': '2026-10-11',
            'description': 'Home Credit Laptop Installment',
            'account_id': self.acc_a1.id,
            'transaction_type': 'EXPENSE',
            'is_debt_payment': 'true',
            'debt_id': debt.id,
            'notes': 'Scanned receipt automated test'
        })

        self.assertRedirects(response, reverse('debts:detail', kwargs={'pk': debt.pk}))

        # Verify transaction created
        tx = Transaction.objects.filter(description='Home Credit Laptop Installment').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, Decimal('2500.00'))

        # Verify linked DebtPayment created and balance updated
        payment = DebtPayment.objects.filter(debt=debt, linked_transaction=tx).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('2500.00'))

        debt.refresh_from_db()
        self.assertEqual(debt.remaining_balance, Decimal('27500.00'))

    def test_monthly_bills_workflow(self):
        from transactions.models import RecurringTransaction
        from datetime import date
        client = Client()
        client.force_login(self.user_a)

        # 1. Access bills list
        response = client.get(reverse('transactions:bills_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monthly Bills & Subscriptions")

        # 2. Create a bill
        create_resp = client.post(reverse('transactions:bill_create'), {
            'description': 'PLDT Home Fiber',
            'amount': '1899.00',
            'account': self.acc_a1.id,
            'frequency': 'MONTHLY',
            'next_run_date': '2026-10-25',
            'is_active': True,
        })
        self.assertRedirects(create_resp, reverse('transactions:bills_list'))

        bill = RecurringTransaction.objects.filter(user=self.user_a, description='PLDT Home Fiber').first()
        self.assertIsNotNone(bill)
        self.assertEqual(bill.amount, Decimal('1899.00'))
        self.assertEqual(bill.next_run_date, date(2026, 10, 25))

        # 3. Pay bill now
        pay_resp = client.post(reverse('transactions:bill_pay', kwargs={'pk': bill.pk}))
        self.assertRedirects(pay_resp, reverse('transactions:bills_list'))

        # Check transaction created
        tx = Transaction.objects.filter(description='PLDT Home Fiber (Paid Bill)').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.amount, Decimal('1899.00'))
        self.assertEqual(tx.account, self.acc_a1)

        # Check next due date rolled to next month
        bill.refresh_from_db()
        self.assertEqual(bill.next_run_date, date(2026, 11, 25))

