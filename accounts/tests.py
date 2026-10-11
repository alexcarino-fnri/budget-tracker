from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from accounts.models import UserProfile

class AccountsAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='Password123!',
            first_name='Juan'
        )

    def test_user_profile_automatically_created(self):
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.default_currency, 'PHP')
        self.assertEqual(self.user.profile.theme_preference, 'dark')

    def test_login_flow(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'Password123!'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('core:dashboard'))

    def test_registration_flow(self):
        response = self.client.post(reverse('accounts:register'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'first_name': 'Maria',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!'
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username='newuser')
        self.assertEqual(new_user.first_name, 'Maria')
        self.assertTrue(hasattr(new_user, 'profile'))

    def test_profile_update(self):
        self.client.login(username='testuser', password='Password123!')
        response = self.client.post(reverse('accounts:profile'), {
            'first_name': 'Juan Carlos',
            'email': 'juancarlos@example.com',
            'default_currency': 'USD',
            'theme_preference': 'light',
            'monthly_budget_alert_threshold': 85
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Juan Carlos')
        self.assertEqual(self.user.profile.default_currency, 'USD')
        self.assertEqual(self.user.profile.theme_preference, 'light')
        self.assertEqual(self.user.profile.monthly_budget_alert_threshold, 85)
