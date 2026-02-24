from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Transaction(models.Model):
    TRANSACTION_TYPE_CHOICES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]
    
    PAY_CYCLE_CHOICES = [
        ('10th', '10th of the Month'),
        ('25th', '25th of the Month'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=7, choices=TRANSACTION_TYPE_CHOICES)
    pay_cycle = models.CharField(max_length=10, choices=PAY_CYCLE_CHOICES, default='10th')
    date = models.DateField(default=timezone.now)
    description = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.type}: {self.amount} - {self.description} ({self.pay_cycle})"

class BudgetGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    limit_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} Goal: {self.limit_amount}"
