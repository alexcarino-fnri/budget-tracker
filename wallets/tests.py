from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from wallets.models import Account
from wallets.services import get_account_balance, get_all_accounts_with_balances
from transactions.models import Transaction

class WalletsTestCase(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='Password123!')
        self.user_b = User.objects.create_user(username='user_b', password='Password123!')

        self.account_a = Account.objects.create(
            user=self.user_a,
            name='BPI Main',
            account_type='BANK',
            opening_balance=Decimal('1000.00')
        )
        self.account_a2 = Account.objects.create(
            user=self.user_a,
            name='GCash',
            account_type='E_WALLET',
            opening_balance=Decimal('500.00')
        )
        self.account_b = Account.objects.create(
            user=self.user_b,
            name='Secret Bank B',
            account_type='BANK',
            opening_balance=Decimal('20000.00')
        )

    def test_balance_calculation_with_income_expense_and_transfers(self):
        # Initial balance
        self.assertEqual(get_account_balance(self.account_a), Decimal('1000.00'))

        # Add Income: +500
        Transaction.objects.create(
            user=self.user_a,
            transaction_type=Transaction.TYPE_INCOME,
            amount=Decimal('500.00'),
            account=self.account_a,
            description='Bonus'
        )
        self.assertEqual(get_account_balance(self.account_a), Decimal('1500.00'))

        # Add Expense: -200
        Transaction.objects.create(
            user=self.user_a,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('200.00'),
            account=self.account_a,
            description='Dinner'
        )
        self.assertEqual(get_account_balance(self.account_a), Decimal('1300.00'))

        # Transfer from Account A to Account A2: 300
        Transaction.objects.create(
            user=self.user_a,
            transaction_type=Transaction.TYPE_TRANSFER,
            amount=Decimal('300.00'),
            account=self.account_a,
            to_account=self.account_a2,
            description='Top up GCash'
        )
        # Account A should have: 1300 - 300 = 1000
        self.assertEqual(get_account_balance(self.account_a), Decimal('1000.00'))
        # Account A2 should have: 500 + 300 = 800
        self.assertEqual(get_account_balance(self.account_a2), Decimal('800.00'))

    def test_permission_scoping_user_cannot_access_other_user_account(self):
        client = Client()
        client.login(username='user_a', password='Password123!')

        # User A tries to view User B's account
        response = client.get(reverse('wallets:detail', kwargs={'pk': self.account_b.pk}))
        self.assertEqual(response.status_code, 404)

        # User A tries to edit User B's account
        response = client.get(reverse('wallets:update', kwargs={'pk': self.account_b.pk}))
        self.assertEqual(response.status_code, 404)

        # User A's list should not contain User B's account
        response = client.get(reverse('wallets:list'))
        self.assertContains(response, 'BPI Main')
        self.assertNotContains(response, 'Secret Bank B')

    def test_currency_selection_and_symbol_display(self):
        # Create USD account
        usd_account = Account.objects.create(
            user=self.user_a,
            name='Chase Checking',
            account_type='BANK',
            currency='USD',
            opening_balance=Decimal('2500.00')
        )
        self.assertEqual(usd_account.currency_symbol, '$')

        client = Client()
        client.login(username='user_a', password='Password123!')
        
        # Test Account List displays '$' for USD account
        response = client.get(reverse('wallets:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Chase Checking')
        self.assertContains(response, '$ 2,500.00')

        # Test Account Detail displays '$'
        detail_response = client.get(reverse('wallets:detail', kwargs={'pk': usd_account.pk}))
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, '$ 2,500.00')

