from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from budgets.models import Category, Budget
from budgets.services import get_monthly_budget_progress, ensure_default_categories
from wallets.models import Account
from transactions.models import Transaction

class BudgetsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='budget_tester', password='Password123!')
        self.account = Account.objects.create(user=self.user, name='Main Account')
        ensure_default_categories(self.user)
        self.food_cat = Category.objects.get(user=self.user, name='Food & Dining')

    def test_default_categories_seeded(self):
        cats = Category.objects.filter(user=self.user)
        self.assertGreater(cats.count(), 10)
        self.assertTrue(cats.filter(name='Salary', category_type='INCOME').exists())
        self.assertTrue(cats.filter(name='Groceries', category_type='EXPENSE').exists())

    def test_budget_progress_thresholds_warning_and_alert(self):
        today = timezone.now().date()
        # Create budget for 1,000
        budget = Budget.objects.create(
            user=self.user,
            category=self.food_cat,
            month=today.month,
            year=today.year,
            amount=Decimal('1000.00'),
            rollover_unused=False
        )

        # 1. Spent 500 (50%) -> NORMAL
        t1 = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TYPE_EXPENSE,
            date=today,
            amount=Decimal('500.00'),
            account=self.account,
            category=self.food_cat,
            description='Dinner 1'
        )
        prog = get_monthly_budget_progress(self.user, today.year, today.month)
        item = prog['items'][0]
        self.assertEqual(item['status'], 'NORMAL')
        self.assertEqual(item['remaining'], Decimal('500.00'))

        # 2. Spent an additional 350 -> Total 850 (85%) -> WARNING
        t2 = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TYPE_EXPENSE,
            date=today,
            amount=Decimal('350.00'),
            account=self.account,
            category=self.food_cat,
            description='Dinner 2'
        )
        prog = get_monthly_budget_progress(self.user, today.year, today.month)
        item = prog['items'][0]
        self.assertEqual(item['status'], 'WARNING')
        self.assertEqual(item['remaining'], Decimal('150.00'))

        # 3. Spent an additional 200 -> Total 1050 (105%) -> ALERT
        t3 = Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TYPE_EXPENSE,
            date=today,
            amount=Decimal('200.00'),
            account=self.account,
            category=self.food_cat,
            description='Dinner 3'
        )
        prog = get_monthly_budget_progress(self.user, today.year, today.month)
        item = prog['items'][0]
        self.assertEqual(item['status'], 'ALERT')
        self.assertEqual(item['remaining'], Decimal('-50.00'))
