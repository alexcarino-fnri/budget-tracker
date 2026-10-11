from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from decimal import Decimal
import random

from wallets.models import Account
from budgets.models import Category, Budget
from budgets.services import ensure_default_categories
from transactions.models import Transaction, RecurringTransaction
from debts.models import Debt, DebtPayment

class Command(BaseCommand):
    help = 'Seeds realistic demo financial data for testing and demonstrations.'

    def handle(self, *args, **options):
        username = 'demo'
        email = 'demo@budgettracker.ph'
        password = 'DemoPass123!'

        user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'first_name': 'Alex'})
        user.set_password(password)
        user.save()

        # Update profile
        if hasattr(user, 'profile'):
            user.profile.default_currency = 'PHP'
            user.profile.theme_preference = 'dark'
            user.profile.monthly_budget_alert_threshold = 80
            user.profile.save()

        self.stdout.write(f'Created/updated demo user: {username} (password: {password})')

        # Clean existing demo user data to avoid duplication
        Transaction.objects.filter(user=user).delete()
        RecurringTransaction.objects.filter(user=user).delete()
        Budget.objects.filter(user=user).delete()
        Debt.objects.filter(user=user).delete()
        Account.objects.filter(user=user).delete()

        # 1. Accounts
        cash = Account.objects.create(user=user, name='Cash in Wallet', account_type='CASH', opening_balance=Decimal('3500.00'), color_hex='#10b981')
        bpi = Account.objects.create(user=user, name='BPI Savings', account_type='BANK', opening_balance=Decimal('52000.00'), color_hex='#3b82f6')
        gcash = Account.objects.create(user=user, name='GCash', account_type='E_WALLET', opening_balance=Decimal('8450.00'), color_hex='#0ea5e9')
        maya = Account.objects.create(user=user, name='Maya Wallet', account_type='E_WALLET', opening_balance=Decimal('4200.00'), color_hex='#14b8a6')
        bdo_card = Account.objects.create(user=user, name='BDO Credit Card', account_type='CREDIT_CARD', opening_balance=Decimal('0.00'), color_hex='#e11d48')

        self.stdout.write('Created accounts: Cash, BPI, GCash, Maya, BDO Credit Card.')

        # 2. Categories
        ensure_default_categories(user)
        cats = {c.name: c for c in Category.objects.filter(user=user)}

        # 3. Monthly Budgets for current month
        today = timezone.now().date()
        m = today.month
        y = today.year

        budget_configs = [
            ('Food & Dining', Decimal('9000.00')),
            ('Groceries', Decimal('12000.00')),
            ('Bills & Utilities', Decimal('6500.00')),
            ('Transportation', Decimal('4000.00')),
            ('Entertainment', Decimal('3000.00')),
            ('Shopping', Decimal('4500.00')),
            ('Subscriptions', Decimal('1500.00')),
        ]

        for cname, limit in budget_configs:
            cat = cats.get(cname)
            if cat:
                Budget.objects.create(
                    user=user,
                    category=cat,
                    month=m,
                    year=y,
                    amount=limit,
                    rollover_unused=True
                )
        self.stdout.write(f'Configured {len(budget_configs)} category budgets for {m}/{y}.')

        # 4. Realistic Transactions across past 60 days
        # Salaries
        for days_ago in (45, 15):
            Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TYPE_INCOME,
                date=today - timedelta(days=days_ago),
                amount=Decimal('38500.00'),
                account=bpi,
                category=cats.get('Salary'),
                description='Semi-Monthly Corporate Salary',
                notes='Direct bank payroll deposit'
            )

        # Freelance Income
        Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TYPE_INCOME,
            date=today - timedelta(days=22),
            amount=Decimal('15000.00'),
            account=gcash,
            category=cats.get('Freelance'),
            description='Web Design Client Milestone #1',
            notes='Paid via GCash'
        )

        # Transfers (BPI to GCash & Cash withdrawal)
        Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TYPE_TRANSFER,
            date=today - timedelta(days=14),
            amount=Decimal('5000.00'),
            account=bpi,
            to_account=gcash,
            description='Transfer BPI to GCash for daily spend',
            notes='Online bank fund transfer'
        )
        Transaction.objects.create(
            user=user,
            transaction_type=Transaction.TYPE_TRANSFER,
            date=today - timedelta(days=10),
            amount=Decimal('3000.00'),
            account=bpi,
            to_account=cash,
            description='ATM Cash Withdrawal',
            notes='Pocket cash'
        )

        # Expenses
        sample_expenses = [
            (today - timedelta(days=28), Decimal('4500.00'), bpi, 'Rent & Housing', 'Apartment Partial Rent Share', 'Transferred to landlord'),
            (today - timedelta(days=25), Decimal('3250.00'), gcash, 'Groceries', 'SM Supermarket Groceries', 'Weekly food supplies'),
            (today - timedelta(days=20), Decimal('1899.00'), bpi, 'Bills & Utilities', 'PLDT Home Fiber Internet', 'Monthly plan 1899'),
            (today - timedelta(days=18), Decimal('2450.00'), bdo_card, 'Shopping', 'Uniqlo Casual Clothes', 'Paid with credit card'),
            (today - timedelta(days=12), Decimal('480.00'), gcash, 'Food & Dining', 'Jollibee Delivery Dinner', 'Burgers and chickenjoy'),
            (today - timedelta(days=9), Decimal('1250.00'), gcash, 'Transportation', 'Grab Car Rides to Makati', 'Work commute'),
            (today - timedelta(days=7), Decimal('3600.00'), gcash, 'Groceries', 'Landers Superstore Run', 'Monthly pantry supplies'),
            (today - timedelta(days=5), Decimal('550.00'), bdo_card, 'Subscriptions', 'Netflix Premium Plan', 'Monthly auto-charge'),
            (today - timedelta(days=3), Decimal('380.00'), cash, 'Food & Dining', 'Starbucks Caramel Macchiato', 'Morning coffee run'),
            (today - timedelta(days=1), Decimal('850.00'), gcash, 'Entertainment', 'Cinema Tickets & Popcorn', 'Weekend movie'),
        ]

        for dt, amt, acc, cname, desc, nts in sample_expenses:
            Transaction.objects.create(
                user=user,
                transaction_type=Transaction.TYPE_EXPENSE,
                date=dt,
                amount=amt,
                account=acc,
                category=cats.get(cname),
                description=desc,
                notes=nts
            )
        self.stdout.write(f'Created {len(sample_expenses) + 4} demo transactions.')

        # 5. Debts (I owe + Owed to me)
        # SSS Salary Loan (I owe)
        sss_debt = Debt.objects.create(
            user=user,
            debt_type=Debt.TYPE_OWED_BY_ME,
            title='SSS Salary Loan',
            creditor_or_debtor='Social Security System (SSS)',
            principal=Decimal('25000.00'),
            interest_rate=Decimal('10.00'),
            start_date=today - timedelta(days=90),
            due_date=today + timedelta(days=275),
            payment_frequency='MONTHLY',
            minimum_payment=Decimal('1150.00'),
            status=Debt.STATUS_ACTIVE,
            notes='2-year term salary loan'
        )
        # Payments made
        DebtPayment.objects.create(
            debt=sss_debt,
            date=today - timedelta(days=60),
            amount=Decimal('2300.00'),
            notes='Installment month 1 & 2'
        )
        DebtPayment.objects.create(
            debt=sss_debt,
            date=today - timedelta(days=20),
            amount=Decimal('1150.00'),
            notes='Installment month 3'
        )

        # Money lent to friend (Owed to me)
        friend_debt = Debt.objects.create(
            user=user,
            debt_type=Debt.TYPE_OWED_TO_ME,
            title='Lent for Laptop Repair',
            creditor_or_debtor='Carlos Mendez (Colleague)',
            principal=Decimal('7000.00'),
            interest_rate=Decimal('0.00'),
            start_date=today - timedelta(days=40),
            due_date=today + timedelta(days=20),
            payment_frequency='ONE_TIME',
            minimum_payment=Decimal('0.00'),
            status=Debt.STATUS_ACTIVE,
            notes='Lent to Carlos for urgent motherboard repair'
        )
        DebtPayment.objects.create(
            debt=friend_debt,
            date=today - timedelta(days=15),
            amount=Decimal('3000.00'),
            notes='Partial return via GCash'
        )

        self.stdout.write('Created demo debts: SSS Loan (I Owe) and Carlos Loan (Owed to Me) with payment records.')

        # 6. Recurring Transactions
        RecurringTransaction.objects.create(
            user=user,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('1899.00'),
            account=bpi,
            category=cats.get('Bills & Utilities'),
            description='PLDT Fiber Internet Auto-Debit',
            frequency='MONTHLY',
            start_date=today,
            next_run_date=today + timedelta(days=12),
            is_active=True
        )
        RecurringTransaction.objects.create(
            user=user,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('550.00'),
            account=bdo_card,
            category=cats.get('Subscriptions'),
            description='Netflix Premium Subscription',
            frequency='MONTHLY',
            start_date=today,
            next_run_date=today + timedelta(days=25),
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS(f'''
=============================================================
✨ DEMO SEED COMPLETED SUCCESSFULLY! ✨
Login Credentials:
  Username: {username}
  Password: {password}
=============================================================
'''))
