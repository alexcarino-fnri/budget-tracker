from django.contrib import admin
from .models import Category, Transaction, BudgetGoal

admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(BudgetGoal)
