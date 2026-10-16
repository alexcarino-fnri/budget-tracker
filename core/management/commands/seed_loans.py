from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from wallets.models import Account
from budgets.models import Category
from budgets.services import ensure_default_categories
from debts.models import Debt, DebtPayment
from transactions.models import RecurringTransaction


class Command(BaseCommand):
    help = 'Seeds initial loans, debts, and monthly bills for the specified user or admin account.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default=None, help='Username to seed data for.')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options.get('username')

        if username:
            user = User.objects.filter(username=username).first()
        else:
            # Find the superuser or first available user
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()

        if not user:
            self.stdout.write(self.style.ERROR("No user found. Create a user first before seeding."))
            return

        self.stdout.write(f"Seeding loans and monthly bills for user: {user.username}...")

        # 1. Ensure Profile Settings
        if hasattr(user, 'profile'):
            user.profile.default_currency = 'PHP'
            user.profile.save()

        # 2. Ensure Categories
        ensure_default_categories(user)
        debt_cat = Category.objects.filter(user=user, name='Debt Payment').first()
        bills_cat = Category.objects.filter(user=user, name='Bills & Utilities').first() or debt_cat

        # 3. Ensure Default Wallets / Accounts with Categories & Credit Card settings
        account_defs = [
            {
                'name': 'BDO Savings Account',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#1d4ed8',
                'balance': Decimal('150000.00'),
                'interest_rate': Decimal('0.125'),
            },
            {
                'name': 'Landbank Payroll',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#15803d',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'UnionBank (Pag-IBIG Loyalty)',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#ea580c',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'Maya Wallet',
                'type': Account.TYPE_E_WALLET,
                'curr': 'PHP',
                'color': '#22c55e',
                'balance': Decimal('0.02'),
            },
            {
                'name': 'Maya Savings',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#10b981',
                'balance': Decimal('0.00'),
                'interest_rate': Decimal('3.50'),
            },
            {
                'name': 'Maya Credit',
                'type': Account.TYPE_CREDIT_CARD,
                'curr': 'PHP',
                'color': '#6366f1',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'Maya Black Credit Card',
                'type': Account.TYPE_CREDIT_CARD,
                'curr': 'PHP',
                'color': '#0f172a',
                'balance': Decimal('-28283.78'),  # Statement Due Oct 30
                'credit_limit': Decimal('44000.00'),
                'unbilled_amount': Decimal('13555.22'),  # 44000 - 2161 - 28283.78 = 13555.22
                'statement_day': 10,
                'due_day': 30,
            },
            {
                'name': 'MariBank',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#f97316',
                'balance': Decimal('890.02'),
                'interest_rate': Decimal('2.50'),
            },
            {
                'name': 'Mari Credit Card',
                'type': Account.TYPE_CREDIT_CARD,
                'curr': 'PHP',
                'color': '#ea580c',
                'balance': Decimal('-15242.48'),  # Statement Due Nov 4
                'credit_limit': Decimal('37000.00'),
                'unbilled_amount': Decimal('50.00'),  # 37000 - 21707.52 - 15242.48 = 50.00
                'statement_day': 14,
                'due_day': 4,
            },
            {
                'name': 'GoTyme',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#06b6d4',
                'balance': Decimal('2.89'),
            },
            {
                'name': 'Go Save (GoTyme)',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#0891b2',
                'balance': Decimal('0.93'),
                'interest_rate': Decimal('4.00'),
            },
            {
                'name': 'GCash',
                'type': Account.TYPE_E_WALLET,
                'curr': 'PHP',
                'color': '#0284c7',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'DiskarTech',
                'type': Account.TYPE_SAVINGS,
                'curr': 'PHP',
                'color': '#f59e0b',
                'balance': Decimal('0.00'),
                'interest_rate': Decimal('3.25'),
            },
            {
                'name': 'Wise',
                'type': Account.TYPE_E_WALLET,
                'curr': 'PHP',
                'color': '#10b981',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'Payoneer (USD)',
                'type': Account.TYPE_E_WALLET,
                'curr': 'USD',
                'color': '#ff4800',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'konek2CARD',
                'type': Account.TYPE_E_WALLET,
                'curr': 'PHP',
                'color': '#64748b',
                'balance': Decimal('0.00'),
            },
            {
                'name': 'Atome',
                'type': Account.TYPE_CREDIT_CARD,
                'curr': 'PHP',
                'color': '#eab308',
                'balance': Decimal('-4427.11'),  # Active monthly installment due Nov 5
                'credit_limit': Decimal('38430.00'),
                'unbilled_amount': Decimal('7326.63'),  # 38430 - 26676.26 - 4427.11 = 7326.63
                'statement_day': 20,
                'due_day': 5,
            },
        ]

        # Clean up previous seeded loans/bills with matching titles to prevent duplicates
        loan_titles = [
            'SPayLater',
            'SLoan 1',
            'SLoan 2',
            'Maya Loan',
            'Appliance Loan (HC)',
            'Apple MacBook Pro (HC)',
            'Cash Loan (HC)',
            'Atome Loan',
            'Trustloan',
            'Tiktok PayLater Bills',
            'Billease',
            'Cash Loan (CB)',
            'Maya Credit Card Bills',
            'Maya Black Credit Card Bills',
            'Mari Credit Card Bills',
            'Maya Easy Credit Bills',
        ]
        Debt.objects.filter(user=user, title__in=loan_titles).delete()
        RecurringTransaction.objects.filter(user=user, description__in=loan_titles).delete()

        # Purge old legacy placeholder accounts if they have no transactions
        legacy_names = ['BPI Savings', 'Cash on Hand', 'Maya Time Deposit', 'Maya Credit Card']
        for leg_acc in Account.objects.filter(user=user, name__in=legacy_names):
            if not leg_acc.transactions_outgoing.exists() and not leg_acc.transactions_incoming.exists():
                leg_acc.delete()

        accounts = {}
        for acc_info in account_defs:
            acc, created = Account.objects.get_or_create(
                user=user,
                name=acc_info['name'],
                defaults={
                    'account_type': acc_info['type'],
                    'currency': acc_info['curr'],
                    'color_hex': acc_info['color'],
                    'opening_balance': acc_info['balance'],
                    'is_active': True,
                    'credit_limit': acc_info.get('credit_limit'),
                    'unbilled_amount': acc_info.get('unbilled_amount', Decimal('0.00')),
                    'statement_day': acc_info.get('statement_day'),
                    'due_day': acc_info.get('due_day'),
                    'interest_rate': acc_info.get('interest_rate'),
                    'maturity_date': acc_info.get('maturity_date'),
                }
            )
            # Update fields if it already existed
            if not created:
                acc.account_type = acc_info['type']
                acc.currency = acc_info['curr']
                acc.color_hex = acc_info['color']
                acc.opening_balance = acc_info['balance']
                acc.credit_limit = acc_info.get('credit_limit')
                acc.unbilled_amount = acc_info.get('unbilled_amount', Decimal('0.00'))
                acc.statement_day = acc_info.get('statement_day')
                acc.due_day = acc_info.get('due_day')
                acc.interest_rate = acc_info.get('interest_rate')
                acc.maturity_date = acc_info.get('maturity_date')
                acc.save()
            accounts[acc_info['name']] = acc

        primary_acc = accounts['BDO Savings Account']
        maya_acc = accounts['Maya Wallet']

        # 5. Define all Loans / Debts and Schedules
        debts_data = [
            {
                'title': 'SPayLater',
                'creditor': 'Shopee / SeaMoney',
                'principal': Decimal('2628.00'),
                'min_payment': Decimal('1479.76'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 5),
                'due_date': date(2027, 1, 5),
                'next_due': date(2026, 11, 5),
                'acc': maya_acc,
                'notes': (
                    "Schedule:\n"
                    "- Nov 5, 2026: ₱1,479.76\n"
                    "- Dec 5, 2026: ₱765.12\n"
                    "- Jan 5, 2027: ₱383.12"
                ),
            },
            {
                'title': 'SLoan 1',
                'creditor': 'Shopee / SeaMoney',
                'principal': Decimal('11954.92'),
                'min_payment': Decimal('2988.73'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 12),
                'due_date': date(2027, 2, 12),
                'next_due': date(2026, 11, 12),
                'acc': primary_acc,
                'notes': (
                    "4 Installments of ₱2,988.73 on the 12th of each month:\n"
                    "- Nov 12, 2026: ₱2,988.73\n"
                    "- Dec 12, 2026: ₱2,988.73\n"
                    "- Jan 12, 2027: ₱2,988.73\n"
                    "- Feb 12, 2027: ₱2,988.73"
                ),
            },
            {
                'title': 'SLoan 2',
                'creditor': 'Shopee / SeaMoney',
                'principal': Decimal('13303.35'),
                'min_payment': Decimal('2217.23'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 9, 21),
                'due_date': date(2027, 3, 21),
                'next_due': date(2026, 10, 21),
                'acc': primary_acc,
                'notes': (
                    "6 Installments on the 21st of each month:\n"
                    "- Oct 21, 2026: ₱2,217.23\n"
                    "- Nov 21, 2026: ₱2,217.23\n"
                    "- Dec 21, 2026: ₱2,217.23\n"
                    "- Jan 21, 2027: ₱2,217.23\n"
                    "- Feb 21, 2027: ₱2,217.23\n"
                    "- Mar 21, 2027: ₱2,217.20"
                ),
            },
            {
                'title': 'Maya Loan',
                'creditor': 'Maya Bank',
                'principal': Decimal('14854.50'),
                'min_payment': Decimal('2475.75'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 9, 23),
                'due_date': date(2027, 3, 23),
                'next_due': date(2026, 10, 23),
                'acc': maya_acc,
                'notes': (
                    "6 Installments of ₱2,475.75 on the 23rd of each month:\n"
                    "- Oct 23, 2026: ₱2,475.75\n"
                    "- Nov 23, 2026: ₱2,475.75\n"
                    "- Dec 23, 2026: ₱2,475.75\n"
                    "- Jan 23, 2027: ₱2,475.75\n"
                    "- Feb 23, 2027: ₱2,475.75\n"
                    "- Mar 23, 2027: ₱2,475.75"
                ),
            },
            {
                'title': 'Appliance Loan (HC)',
                'creditor': 'Home Credit',
                'principal': Decimal('42900.00'),
                'min_payment': Decimal('3900.00'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 30),
                'due_date': date(2027, 9, 30),
                'next_due': date(2026, 11, 30),
                'acc': primary_acc,
                'notes': (
                    "11 Monthly installments of ₱3,900.00 due on the 30th:\n"
                    "Nov 30, Dec 30, Jan 30, Feb 28, Mar 30, Apr 30, May 30, Jun 30, Jul 30, Aug 30, Sep 30, 2027"
                ),
            },
            {
                'title': 'Apple MacBook Pro (HC)',
                'creditor': 'Home Credit',
                'principal': Decimal('171624.00'),
                'min_payment': Decimal('7151.00'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 2),
                'due_date': date(2028, 10, 2),
                'next_due': date(2026, 11, 2),
                'acc': primary_acc,
                'notes': "24 Months installment plan of ₱7,151.00 due on the 2nd of each month (Until Oct 2028).",
            },
            {
                'title': 'Cash Loan (HC)',
                'creditor': 'Home Credit',
                'principal': Decimal('313200.00'),
                'min_payment': Decimal('6525.00'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 1),
                'due_date': date(2030, 10, 1),
                'next_due': date(2026, 11, 1),
                'acc': primary_acc,
                'notes': "48 Months installment plan of ₱6,525.00 due on the 1st of each month (Until Oct 2030).",
            },
            {
                'title': 'Atome Loan',
                'creditor': 'Atome',
                'principal': Decimal('30989.77'),
                'min_payment': Decimal('4427.11'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 5),
                'due_date': date(2027, 5, 5),
                'next_due': date(2026, 11, 5),
                'acc': accounts['Atome'],
                'notes': "7 Monthly installments of ₱4,427.11 due on the 5th (Until May 5, 2027).",
            },
            {
                'title': 'Trustloan',
                'creditor': 'Trust Bank',
                'principal': Decimal('6650.00'),
                'min_payment': Decimal('1330.00'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 6),
                'due_date': date(2027, 3, 6),
                'next_due': date(2026, 11, 6),
                'acc': primary_acc,
                'notes': "5 Monthly installments of ₱1,330.00 due on the 6th (Until March 6, 2027).",
            },
            {
                'title': 'Tiktok PayLater Bills',
                'creditor': 'TikTok Shop',
                'principal': Decimal('1518.72'),
                'min_payment': Decimal('1518.72'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 15),
                'due_date': date(2026, 11, 15),
                'next_due': date(2026, 11, 15),
                'acc': maya_acc,
                'notes': "TikTok PayLater bill due November 15, 2026: ₱1,518.72.",
            },
            {
                'title': 'Billease',
                'creditor': 'Billease',
                'principal': Decimal('28633.62'),
                'min_payment': Decimal('4772.27'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 8, 10),
                'due_date': date(2027, 1, 10),
                'next_due': date(2026, 11, 10),
                'acc': primary_acc,
                'has_past_payments': True,
                'notes': (
                    "6 Installments of ₱4,772.27 on the 10th:\n"
                    "- Aug 10, 2026: ₱4,772.27 (Paid)\n"
                    "- Sep 10, 2026: ₱4,772.27 (Paid)\n"
                    "- Oct 10, 2026: ₱4,772.27 (Paid)\n"
                    "- Nov 10, 2026: ₱4,772.27 (Upcoming)\n"
                    "- Dec 10, 2026: ₱4,772.27 (Upcoming)\n"
                    "- Jan 10, 2027: ₱4,772.27 (Upcoming)"
                ),
            },
            {
                'title': 'Cash Loan (CB)',
                'creditor': 'CitySavings / CB',
                'principal': Decimal('273520.00'),
                'min_payment': Decimal('5260.00'),
                'frequency': Debt.FREQ_WEEKLY,
                'start_date': date(2026, 10, 16),
                'due_date': date(2027, 10, 15),
                'next_due': date(2026, 10, 23),
                'acc': primary_acc,
                'notes': "₱5,260.00 every Friday for 1 year (52 weekly payments).",
            },
            {
                'title': 'Maya Black Credit Card Bills',
                'creditor': 'Maya Bank',
                'principal': Decimal('28283.78'),
                'min_payment': Decimal('28283.78'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 1),
                'due_date': date(2026, 10, 30),
                'next_due': date(2026, 10, 30),
                'acc': accounts['Maya Black Credit Card'],
                'notes': "Credit card statement bill due October 30, 2026: ₱28,283.78.",
            },
            {
                'title': 'Mari Credit Card Bills',
                'creditor': 'MariBank',
                'principal': Decimal('15242.48'),
                'min_payment': Decimal('15242.48'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 5),
                'due_date': date(2026, 11, 4),
                'next_due': date(2026, 11, 4),
                'acc': accounts['Mari Credit Card'],
                'notes': "Credit card statement bill due November 4, 2026: ₱15,242.48.",
            },
            {
                'title': 'Maya Easy Credit Bills',
                'creditor': 'Maya Bank',
                'principal': Decimal('5915.34'),
                'min_payment': Decimal('5915.34'),
                'frequency': Debt.FREQ_MONTHLY,
                'start_date': date(2026, 10, 19),
                'due_date': date(2026, 11, 19),
                'next_due': date(2026, 11, 19),
                'acc': accounts['Maya Credit'],
                'notes': "Maya Easy Credit revolving line bill due November 19, 2026: ₱5,915.34.",
            },
        ]

        created_debts = 0
        created_bills = 0

        for item in debts_data:
            debt = Debt.objects.create(
                user=user,
                debt_type=Debt.TYPE_OWED_BY_ME,
                title=item['title'],
                creditor_or_debtor=item['creditor'],
                principal=item['principal'],
                minimum_payment=item['min_payment'],
                payment_frequency=item['frequency'],
                start_date=item['start_date'],
                due_date=item['due_date'],
                notes=item['notes'],
                status=Debt.STATUS_ACTIVE,
            )
            created_debts += 1

            # If item has past payments (Billease: Aug, Sep, Oct), record them
            if item.get('has_past_payments'):
                DebtPayment.objects.create(
                    debt=debt,
                    date=date(2026, 8, 10),
                    amount=Decimal('4772.27'),
                    notes='Aug 10 installment payment'
                )
                DebtPayment.objects.create(
                    debt=debt,
                    date=date(2026, 9, 10),
                    amount=Decimal('4772.27'),
                    notes='Sep 10 installment payment'
                )
                DebtPayment.objects.create(
                    debt=debt,
                    date=date(2026, 10, 10),
                    amount=Decimal('4772.27'),
                    notes='Oct 10 installment payment'
                )

            # Create corresponding Recurring Bill so it shows up in Monthly Bills and Dashboard
            bill_freq = (
                RecurringTransaction.FREQ_WEEKLY
                if item['frequency'] == Debt.FREQ_WEEKLY
                else RecurringTransaction.FREQ_MONTHLY
            )
            RecurringTransaction.objects.create(
                user=user,
                transaction_type='EXPENSE',
                description=item['title'],
                amount=item['min_payment'],
                frequency=bill_freq,
                start_date=item['start_date'],
                next_run_date=item['next_due'],
                end_date=item['due_date'],
                account=item['acc'],
                category=debt_cat or bills_cat,
                is_active=True,
            )
            created_bills += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {created_debts} Debt records and {created_bills} Monthly Bills for user '{user.username}'."
        ))
