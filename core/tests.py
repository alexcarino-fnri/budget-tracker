from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from debts.models import Debt
from core.models import NotificationDismissal
from core.context_processors import global_finance_context

class NotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client = Client()
        self.client.login(username='testuser', password='password123')

        # Create upcoming debt
        self.debt = Debt.objects.create(
            user=self.user,
            title='Credit Card Bill',
            debt_type='OWED_BY_ME',
            creditor_or_debtor='BDO Bank',
            principal=Decimal('5000.00'),
            start_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=5)
        )

    def test_notification_appears_in_context(self):
        response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Credit Card Bill')
        self.assertEqual(response.context['notifications_count'], 1)

    def test_read_and_redirect_notification(self):
        notif_key = f"debt-{self.debt.id}-{self.debt.due_date}"
        target_url = f"/debts/{self.debt.id}/"
        url = reverse('core:read_and_redirect_notification', kwargs={'key': notif_key})
        
        response = self.client.get(f"{url}?next={target_url}")
        self.assertRedirects(response, target_url)

        # Check dismissal was recorded
        self.assertTrue(NotificationDismissal.objects.filter(user=self.user, notification_key=notif_key).exists())

        # Check notification no longer appears in dashboard
        dashboard_response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dashboard_response.context['notifications_count'], 0)

    def test_clear_individual_notification(self):
        notif_key = f"debt-{self.debt.id}-{self.debt.due_date}"
        url = reverse('core:clear_notification', kwargs={'key': notif_key})
        
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(NotificationDismissal.objects.filter(user=self.user, notification_key=notif_key).exists())

        dashboard_response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dashboard_response.context['notifications_count'], 0)

    def test_clear_all_notifications(self):
        url = reverse('core:clear_all_notifications')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        dashboard_response = self.client.get(reverse('core:dashboard'))
        self.assertEqual(dashboard_response.context['notifications_count'], 0)
