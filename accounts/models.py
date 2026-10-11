from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class UserProfile(models.Model):
    THEME_CHOICES = [
        ('system', 'System Default'),
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
    ]

    CURRENCY_CHOICES = [
        ('PHP', 'PHP (₱ - Philippine Peso)'),
        ('USD', 'USD ($ - US Dollar)'),
        ('EUR', 'EUR (€ - Euro)'),
        ('GBP', 'GBP (£ - British Pound)'),
        ('JPY', 'JPY (¥ - Japanese Yen)'),
        ('CAD', 'CAD (CA$ - Canadian Dollar)'),
        ('AUD', 'AUD (A$ - Australian Dollar)'),
        ('SGD', 'SGD (S$ - Singapore Dollar)'),
        ('HKD', 'HKD (HK$ - Hong Kong Dollar)'),
        ('CNY', 'CNY (¥ - Chinese Yuan)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    default_currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='PHP')
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    monthly_budget_alert_threshold = models.PositiveIntegerField(default=80, help_text="Percentage to trigger warning (e.g. 80%)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(post_save, sender=User)
def create_or_save_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
