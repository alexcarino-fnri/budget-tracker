from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from wallets.models import Account
from transactions.models import Transaction
from budgets.models import Category
from io import BytesIO

class ReportsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='report_user', password='Password123!')
        self.account = Account.objects.create(user=self.user, name='Cash')
        self.cat = Category.objects.create(user=self.user, name='Food', category_type='EXPENSE')
        Transaction.objects.create(
            user=self.user,
            transaction_type=Transaction.TYPE_EXPENSE,
            amount=Decimal('120.00'),
            account=self.account,
            category=self.cat,
            description='Test Lunch'
        )

    def test_csv_export_endpoint(self):
        client = Client()
        client.login(username='report_user', password='Password123!')
        response = client.get(reverse('reports:export_transactions_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('Test Lunch', response.content.decode('utf-8'))

    def test_excel_export_endpoint(self):
        client = Client()
        client.login(username='report_user', password='Password123!')
        response = client.get(reverse('reports:export_transactions_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('spreadsheetml', response['Content-Type'])

    def test_csv_import_flow_with_preview(self):
        client = Client()
        client.login(username='report_user', password='Password123!')

        csv_content = b"Date,Type,Amount,Account,Category,Description,Notes\n2026-10-10,EXPENSE,250.00,Cash,Food,Dinner,Team Dinner\n"
        csv_file = BytesIO(csv_content)
        csv_file.name = 'test_import.csv'

        # Step 1: Upload & Preview
        response = client.post(reverse('reports:import'), {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dinner')
        self.assertContains(response, '250.00')

        # Step 2: Confirm import
        response = client.post(reverse('reports:import'), {'confirm_import': '1'})
        self.assertEqual(response.status_code, 302)

        # Check transaction saved
        imported_tx = Transaction.objects.filter(description='Dinner').first()
        self.assertIsNotNone(imported_tx)
        self.assertEqual(imported_tx.amount, Decimal('250.00'))
