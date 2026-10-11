from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('CASH', 'Cash'),
        ('BANK', 'Bank Account'),
        ('E_WALLET', 'E-wallet (GCash, Maya)'),
        ('CREDIT_CARD', 'Credit Card'),
        ('OTHER', 'Other'),
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

    CURRENCY_SYMBOLS = {
        'PHP': '₱',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥',
        'CAD': 'CA$',
        'AUD': 'A$',
        'SGD': 'S$',
        'HKD': 'HK$',
        'CNY': '¥',
    }

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='CASH')
    currency = models.CharField(max_length=5, choices=CURRENCY_CHOICES, default='PHP')
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    color_hex = models.CharField(max_length=7, default='#10b981')
    is_active = models.BooleanField(default=True)

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get((self.currency or '').upper(), self.currency or '₱')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name'], name='unique_user_account_name')
        ]
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"
