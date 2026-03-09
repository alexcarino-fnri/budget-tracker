from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    monthly_income_goal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency_symbol = models.CharField(max_length=5, default='₱')

    def __str__(self):
        return f"{self.user.username}'s Profile"

class PayCycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pay_cycles')
    name = models.CharField(max_length=50)
    start_day = models.PositiveIntegerField()
    
    class Meta:
        ordering = ['start_day']

    def __str__(self):
        return f"{self.name} (Starts on {self.start_day})"

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
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=7, choices=TRANSACTION_TYPE_CHOICES)
    pay_cycle = models.ForeignKey(PayCycle, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True) # New field for bills
    description = models.TextField(blank=True)
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        cycle_name = self.pay_cycle.name if self.pay_cycle else "No Cycle"
        return f"{self.type}: {self.amount} - {self.description} ({cycle_name})"

class BudgetGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    limit_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} Goal: {self.limit_amount}"
