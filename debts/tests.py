from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from debts.models import Debt, DebtPayment
from debts.services import get_debt_summary, compare_payoff_strategies
from wallets.models import Account
from transactions.models import Transaction

class DebtsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='Password123!')
        self.user_b = User.objects.create_user(username='user_b', password='Password123!')

        self.account_a = Account.objects.create(
            user=self.user_a,
            name='BPI Payroll',
            opening_balance=Decimal('20000.00')
        )

        today = timezone.now().date()

        # Debt 1: Small balance (5,000), low interest (5%)
        self.debt1 = Debt.objects.create(
            user=self.user_a,
            debt_type=Debt.TYPE_OWED_BY_ME,
            title='Small Debt',
            creditor_or_debtor='Credit Card A',
            principal=Decimal('5000.00'),
            interest_rate=Decimal('5.00'),
            start_date=today - timedelta(days=30),
            due_date=today + timedelta(days=60),
            payment_frequency='MONTHLY',
            minimum_payment=Decimal('500.00')
        )

        # Debt 2: Higher balance (15,000), high interest (24%)
        self.debt2 = Debt.objects.create(
            user=self.user_a,
            debt_type=Debt.TYPE_OWED_BY_ME,
            title='High Interest Debt',
            creditor_or_debtor='Credit Card B',
            principal=Decimal('15000.00'),
            interest_rate=Decimal('24.00'),
            start_date=today - timedelta(days=30),
            due_date=today + timedelta(days=120),
            payment_frequency='MONTHLY',
            minimum_payment=Decimal('1000.00')
        )

        # Debt for user B
        self.debt_b = Debt.objects.create(
            user=self.user_b,
            debt_type=Debt.TYPE_OWED_BY_ME,
            title='Private loan user B',
            creditor_or_debtor='Bank XYZ',
            principal=Decimal('50000.00'),
            due_date=today + timedelta(days=300)
        )

    def test_debt_payment_and_remaining_balance(self):
        # Initial summary
        s1 = get_debt_summary(self.debt1)
        self.assertEqual(s1['remaining_balance'], Decimal('5000.00'))
        self.assertEqual(s1['percent_paid'], Decimal('0.0'))

        # Make payment of 2,000
        p = DebtPayment.objects.create(
            debt=self.debt1,
            amount=Decimal('2000.00')
        )
        s2 = get_debt_summary(self.debt1)
        self.assertEqual(s2['remaining_balance'], Decimal('3000.00'))
        self.assertEqual(s2['percent_paid'], Decimal('40.0'))

    def test_payment_with_linked_transaction(self):
        client = Client()
        client.login(username='user_a', password='Password123!')

        response = client.post(reverse('debts:payment_add', kwargs={'pk': self.debt1.pk}), {
            'date': timezone.now().date().strftime('%Y-%m-%d'),
            'amount': '1500.00',
            'notes': 'Installment with sync',
            'create_transaction': 'on',
            'account': str(self.account_a.pk),
        })
        self.assertEqual(response.status_code, 302)

        # Check payment exists
        payment = DebtPayment.objects.filter(debt=self.debt1).first()
        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal('1500.00'))
        self.assertIsNotNone(payment.linked_transaction)
        self.assertEqual(payment.linked_transaction.amount, Decimal('1500.00'))
        self.assertEqual(payment.linked_transaction.transaction_type, Transaction.TYPE_EXPENSE)

    def test_payoff_planner_snowball_vs_avalanche(self):
        comparison = compare_payoff_strategies(self.user_a, extra_monthly=Decimal('1000.00'), selected_strategy='DUE_DATE')
        self.assertIn('snowball', comparison)
        self.assertIn('avalanche', comparison)
        self.assertIn('due_date', comparison)
        self.assertGreater(comparison['snowball']['months'], 0)
        self.assertGreater(comparison['avalanche']['months'], 0)
        self.assertGreater(comparison['due_date']['months'], 0)
        # Avalanche should pay less or equal total interest than Snowball
        self.assertLessEqual(comparison['avalanche']['total_interest'], comparison['snowball']['total_interest'])
        # Verify schedule generation
        self.assertTrue(len(comparison['avalanche']['monthly_schedule']) > 0)
        self.assertTrue(len(comparison['due_date']['debt_summaries']) == 2)

    def test_permission_scoping_user_cannot_access_other_user_debt(self):
        client = Client()
        client.login(username='user_a', password='Password123!')

        # User A tries to view User B's debt detail
        response = client.get(reverse('debts:detail', kwargs={'pk': self.debt_b.pk}))
        self.assertEqual(response.status_code, 404)

        # User A tries to edit User B's debt
        response = client.get(reverse('debts:update', kwargs={'pk': self.debt_b.pk}))
        self.assertEqual(response.status_code, 404)

        # User A tries to post a payment to User B's debt
        response = client.post(reverse('debts:payment_add', kwargs={'pk': self.debt_b.pk}), {
            'amount': '500.00',
            'date': timezone.now().date().strftime('%Y-%m-%d'),
        })
        self.assertEqual(response.status_code, 404)
