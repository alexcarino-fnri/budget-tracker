from django import forms
from django.db import models
from django.utils import timezone
from .models import Transaction, RecurringTransaction
from wallets.models import Account
from budgets.models import Category

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ('date', 'transaction_type', 'amount', 'account', 'to_account', 'category', 'description', 'notes', 'receipt')
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'id': 'id_transaction_type',
                'onchange': 'handleTypeChange(this.value)'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 text-lg font-mono font-bold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'placeholder': '0.00',
                'min': '0.01'
            }),
            'account': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'to_account': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. Lunch at Jollibee, Freelance Project, Meralco Bill'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'rows': 2,
                'placeholder': 'Optional details or remarks...'
            }),
            'receipt': forms.FileInput(attrs={
                'class': 'w-full text-xs text-slate-500 dark:text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100 dark:file:bg-emerald-950 dark:file:text-emerald-300'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()

        if self.user:
            self.fields['account'].queryset = Account.objects.filter(user=self.user, is_active=True)
            self.fields['to_account'].queryset = Account.objects.filter(user=self.user, is_active=True)
            self.fields['category'].queryset = Category.objects.filter(
                models.Q(user=self.user) | models.Q(user__isnull=True)
            ).order_by('category_type', 'name')
            self.fields['to_account'].required = False
            self.fields['category'].required = False

    def clean(self):
        cleaned_data = super().clean()
        tx_type = cleaned_data.get('transaction_type')
        account = cleaned_data.get('account')
        to_account = cleaned_data.get('to_account')

        if tx_type == Transaction.TYPE_TRANSFER:
            if not to_account:
                self.add_error('to_account', 'Destination account is required for transfers.')
            elif account == to_account:
                self.add_error('to_account', 'Source and destination accounts must be different.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class BillForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = ('description', 'amount', 'account', 'category', 'frequency', 'next_run_date', 'end_date', 'is_active')
        labels = {
            'description': 'Bill / Subscription Name',
            'amount': 'Bill Amount',
            'account': 'Payment Account / Wallet',
            'category': 'Category',
            'frequency': 'Billing Cycle',
            'next_run_date': 'Next Due Date',
            'end_date': 'End Date (Optional)',
            'is_active': 'Active Reminder',
        }
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. Meralco Electricity, PLDT Fiber, Netflix 4K, Gym Membership',
                'required': 'required'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 text-lg font-mono font-bold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'placeholder': '0.00',
                'min': '0.01',
                'required': 'required'
            }),
            'account': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'required': 'required'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'frequency': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'required': 'required'
            }),
            'next_run_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'required': 'required'
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-4 h-4 text-emerald-600 rounded border-slate-300 focus:ring-emerald-500'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.initial.get('next_run_date'):
            self.initial['next_run_date'] = timezone.now().date()
        if not self.initial.get('frequency'):
            self.initial['frequency'] = RecurringTransaction.FREQ_MONTHLY

        if self.user:
            self.fields['account'].queryset = Account.objects.filter(user=self.user, is_active=True)
            self.fields['category'].queryset = Category.objects.filter(
                models.Q(user=self.user) | models.Q(user__isnull=True)
            ).order_by('category_type', 'name')
            self.fields['category'].required = False

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        # Bills are expenses
        instance.transaction_type = Transaction.TYPE_EXPENSE
        if not instance.start_date:
            instance.start_date = instance.next_run_date
        if commit:
            instance.save()
        return instance

