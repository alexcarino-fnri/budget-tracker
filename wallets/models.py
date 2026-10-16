from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    TYPE_SAVINGS = 'SAVINGS'
    TYPE_E_WALLET = 'E_WALLET'
    TYPE_CREDIT_CARD = 'CREDIT_CARD'
    TYPE_TIME_DEPOSIT = 'TIME_DEPOSIT'
    TYPE_CASH = 'CASH'
    TYPE_CHECKING = 'CHECKING'
    TYPE_INVESTMENT = 'INVESTMENT'
    TYPE_BANK = 'BANK'
    TYPE_OTHER = 'OTHER'

    ACCOUNT_TYPES = [
        (TYPE_SAVINGS, 'Savings Account (Digital / Bank)'),
        (TYPE_E_WALLET, 'e-Wallet (GCash, Maya, ShopeePay)'),
        (TYPE_CREDIT_CARD, 'Credit Card'),
        (TYPE_TIME_DEPOSIT, 'Time Deposit / Stash'),
        (TYPE_CASH, 'Physical Cash on Hand'),
        (TYPE_CHECKING, 'Checking Account'),
        (TYPE_INVESTMENT, 'Investment (MP2, Stocks, Crypto)'),
        (TYPE_BANK, 'Traditional Bank Account'),
        (TYPE_OTHER, 'Other / Custom'),
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

    # Credit Card tracking fields
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), null=True, blank=True,
        help_text="Total approved credit limit (for Credit Cards)"
    )
    unbilled_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'), null=True, blank=True,
        help_text="Unbilled charges / pending purchases since last statement cut"
    )
    statement_day = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Day of the month when statement is generated (1-31)"
    )
    due_day = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Day of the month when payment is due (1-31)"
    )

    # Time Deposit & Savings fields
    interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'), null=True, blank=True,
        help_text="Annual interest rate / p.a. (%)"
    )
    maturity_date = models.DateField(
        null=True, blank=True,
        help_text="Maturity date for Time Deposits"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def currency_symbol(self):
        return self.CURRENCY_SYMBOLS.get((self.currency or '').upper(), self.currency or '₱')

    @property
    def is_credit_card(self):
        return self.account_type == 'CREDIT_CARD'

    @property
    def is_time_deposit(self):
        return self.account_type == 'TIME_DEPOSIT'

    @property
    def is_savings(self):
        return self.account_type in ('SAVINGS', 'BANK')

    @property
    def icon_name(self):
        icon_map = {
            'SAVINGS': 'landmark',
            'BANK': 'landmark',
            'E_WALLET': 'smartphone',
            'CREDIT_CARD': 'credit-card',
            'TIME_DEPOSIT': 'lock',
            'CASH': 'banknote',
            'CHECKING': 'file-text',
            'INVESTMENT': 'trending-up',
            'OTHER': 'wallet',
        }
        return icon_map.get(self.account_type, 'wallet')

    @property
    def billed_amount(self):
        """
        Billed balance from statement for credit cards.
        In accounting, credit card liability is negative balance (or user-entered statement debt).
        """
        if not self.is_credit_card:
            return Decimal('0.00')
        bal = getattr(self, 'current_balance', None)
        if bal is None:
            try:
                from wallets.services import get_account_balance
                bal = get_account_balance(self)
            except Exception:
                bal = self.opening_balance

        if bal < Decimal('0.00'):
            return abs(bal)
        # If user entered opening balance as positive debt and no transactions exist
        if bal > Decimal('0.00') and self.opening_balance > Decimal('0.00'):
            return bal
        return Decimal('0.00')

    @property
    def total_unbilled(self):
        if not self.is_credit_card:
            return Decimal('0.00')
        return self.unbilled_amount or Decimal('0.00')

    @property
    def total_outstanding_credit(self):
        """
        Total credit used = Billed statement balance + Unbilled charges.
        """
        if not self.is_credit_card:
            return Decimal('0.00')
        return self.billed_amount + self.total_unbilled

    @property
    def remaining_credit(self):
        """
        Remaining Available Credit = Total Credit Limit - Total Outstanding (Billed + Unbilled).
        """
        if not self.is_credit_card:
            return Decimal('0.00')
        limit = self.credit_limit or Decimal('0.00')
        if limit <= Decimal('0.00'):
            return Decimal('0.00')
        return max(Decimal('0.00'), limit - self.total_outstanding_credit)

    @property
    def credit_utilization(self):
        """
        Credit utilization percentage (0.0% to 100.0%).
        """
        if not self.is_credit_card or not self.credit_limit or self.credit_limit <= Decimal('0.00'):
            return Decimal('0.00')
        util = (self.total_outstanding_credit / self.credit_limit) * 100
        return min(Decimal('100.00'), util.quantize(Decimal('0.1')))

    @property
    def credit_utilization_color(self):
        """
        Color based on credit utilization: healthy (<30%), warning (30-70%), high (>70%).
        """
        util = self.credit_utilization
        if util < Decimal('30.0'):
            return 'emerald'
        elif util <= Decimal('70.0'):
            return 'amber'
        return 'rose'

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
