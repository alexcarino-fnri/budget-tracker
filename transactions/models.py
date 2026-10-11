from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class Transaction(models.Model):
    TYPE_INCOME = 'INCOME'
    TYPE_EXPENSE = 'EXPENSE'
    TYPE_TRANSFER = 'TRANSFER'

    TRANSACTION_TYPES = [
        (TYPE_INCOME, 'Income'),
        (TYPE_EXPENSE, 'Expense'),
        (TYPE_TRANSFER, 'Transfer'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    account = models.ForeignKey('wallets.Account', on_delete=models.PROTECT, related_name='transactions_outgoing')
    to_account = models.ForeignKey('wallets.Account', on_delete=models.PROTECT, related_name='transactions_incoming', null=True, blank=True)
    category = models.ForeignKey('budgets.Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    description = models.CharField(max_length=255)
    notes = models.TextField(blank=True, default='')
    receipt = models.ImageField(upload_to='receipts/%Y/%m/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'transaction_type']),
            models.Index(fields=['user', 'account']),
        ]

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= Decimal('0.00'):
            raise ValidationError({'amount': 'Amount must be greater than zero.'})

        if self.transaction_type == self.TYPE_TRANSFER:
            if not self.to_account:
                raise ValidationError({'to_account': 'Destination account is required for transfers.'})
            if self.account == self.to_account:
                raise ValidationError({'to_account': 'Cannot transfer money to the same account.'})
        else:
            if self.to_account is not None:
                self.to_account = None

    def __str__(self):
        return f"{self.date} - {self.get_transaction_type_display()}: {self.description} ({self.amount})"


class RecurringTransaction(models.Model):
    FREQ_DAILY = 'DAILY'
    FREQ_WEEKLY = 'WEEKLY'
    FREQ_BIWEEKLY = 'BIWEEKLY'
    FREQ_MONTHLY = 'MONTHLY'
    FREQ_YEARLY = 'YEARLY'

    FREQUENCY_CHOICES = [
        (FREQ_DAILY, 'Daily'),
        (FREQ_WEEKLY, 'Weekly'),
        (FREQ_BIWEEKLY, 'Bi-weekly'),
        (FREQ_MONTHLY, 'Monthly'),
        (FREQ_YEARLY, 'Yearly'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    transaction_type = models.CharField(max_length=10, choices=Transaction.TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    account = models.ForeignKey('wallets.Account', on_delete=models.PROTECT, related_name='recurring_outgoing')
    to_account = models.ForeignKey('wallets.Account', on_delete=models.PROTECT, related_name='recurring_incoming', null=True, blank=True)
    category = models.ForeignKey('budgets.Category', on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transactions')
    description = models.CharField(max_length=255)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default=FREQ_MONTHLY)
    start_date = models.DateField(default=timezone.now)
    next_run_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_run_date']

    def clean(self):
        super().clean()
        if self.transaction_type == Transaction.TYPE_TRANSFER:
            if not self.to_account:
                raise ValidationError({'to_account': 'Destination account is required for recurring transfers.'})
            if self.account == self.to_account:
                raise ValidationError({'to_account': 'Source and destination accounts must be different.'})
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'End date cannot be earlier than start date.'})

    def __str__(self):
        return f"[Recurring {self.frequency}] {self.description} ({self.amount})"
