from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal

class Debt(models.Model):
    TYPE_OWED_BY_ME = 'OWED_BY_ME'  # I owe
    TYPE_OWED_TO_ME = 'OWED_TO_ME'  # Owed to me

    DEBT_TYPES = [
        (TYPE_OWED_BY_ME, 'I Owe (Liability)'),
        (TYPE_OWED_TO_ME, 'Owed to Me (Asset/Receivable)'),
    ]

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_PAID = 'PAID'
    STATUS_OVERDUE = 'OVERDUE'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAID, 'Paid in Full'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    FREQ_MONTHLY = 'MONTHLY'
    FREQ_WEEKLY = 'WEEKLY'
    FREQ_BIWEEKLY = 'BIWEEKLY'
    FREQ_ONE_TIME = 'ONE_TIME'

    PAYMENT_FREQUENCIES = [
        (FREQ_MONTHLY, 'Monthly'),
        (FREQ_WEEKLY, 'Weekly'),
        (FREQ_BIWEEKLY, 'Bi-weekly'),
        (FREQ_ONE_TIME, 'One-time lump sum'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='debts')
    debt_type = models.CharField(max_length=15, choices=DEBT_TYPES, default=TYPE_OWED_BY_ME)
    creditor_or_debtor = models.CharField(max_length=150, help_text="Name of creditor or debtor")
    title = models.CharField(max_length=150, help_text="e.g. Car Loan, Cash Lent to John, BDO Card Installment")
    principal = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    interest_rate = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), help_text="Annual Interest Rate (%)")
    start_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    payment_frequency = models.CharField(max_length=15, choices=PAYMENT_FREQUENCIES, default=FREQ_MONTHLY)
    minimum_payment = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date', 'principal']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'due_date']),
            models.Index(fields=['user', 'debt_type']),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.due_date and self.due_date < self.start_date:
            raise ValidationError({'due_date': 'Due date cannot be earlier than start date.'})

    @property
    def remaining_balance(self):
        if hasattr(self, '_remaining_balance'):
            return self._remaining_balance
        total_paid = self.payments.aggregate(tot=models.Sum('amount'))['tot'] or Decimal('0.00')
        return max(Decimal('0.00'), self.principal - total_paid)

    @remaining_balance.setter
    def remaining_balance(self, value):
        self._remaining_balance = value

    @property
    def currency_symbol(self):
        # Look up user's primary or active account currency, default to ₱
        acc = self.user.financial_accounts.filter(is_active=True).first()
        return acc.currency_symbol if acc else '₱'

    def __str__(self):
        return f"[{self.get_debt_type_display()}] {self.title} - {self.creditor_or_debtor} ({self.principal})"


class DebtPayment(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payments')
    date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    notes = models.CharField(max_length=255, blank=True, default='')
    linked_transaction = models.ForeignKey('transactions.Transaction', on_delete=models.SET_NULL, null=True, blank=True, related_name='debt_payments')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"Payment of {self.amount} for {self.debt.title} on {self.date}"
