from django import forms
from .models import Transaction, Category, BudgetGoal

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['category', 'amount', 'type', 'pay_cycle', 'date', 'description', 'is_paid']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'pay_cycle': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_paid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Groceries'}),
        }

class BudgetGoalForm(forms.ModelForm):
    class Meta:
        model = BudgetGoal
        fields = ['category', 'limit_amount']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'limit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
