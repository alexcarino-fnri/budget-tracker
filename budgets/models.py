from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class Category(models.Model):
    CATEGORY_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories', null=True, blank=True)
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='EXPENSE')
    icon = models.CharField(max_length=50, default='tag', help_text="Lucide icon identifier")
    color = models.CharField(max_length=7, default='#10b981')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['category_type', 'name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'name', 'category_type'], name='unique_user_category_name_type')
        ]

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"


class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    month = models.PositiveSmallIntegerField(help_text="Month number 1-12")
    year = models.PositiveSmallIntegerField(help_text="Year e.g. 2026")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    rollover_unused = models.BooleanField(default=False, help_text="Roll over remaining balance to next month")
    rollover_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), help_text="Amount carried over from previous period")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month', 'category__name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'category', 'year', 'month'], name='unique_user_category_month_year')
        ]
        indexes = [
            models.Index(fields=['user', 'year', 'month']),
        ]

    def __str__(self):
        return f"{self.category.name} Budget - {self.month}/{self.year}: {self.amount}"
