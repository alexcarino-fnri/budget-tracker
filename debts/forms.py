from django import forms
from django.utils import timezone
from .models import Debt, DebtPayment
from wallets.models import Account
from transactions.models import Transaction
from budgets.models import Category
from decimal import Decimal

class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = (
            'debt_type', 'title', 'creditor_or_debtor', 'principal', 
            'interest_rate', 'start_date', 'due_date', 'payment_frequency', 
            'minimum_payment', 'notes'
        )
        widgets = {
            'debt_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. SSS Salary Loan, Car Loan, Lent money to Mark'
            }),
            'creditor_or_debtor': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. BDO, SSS, Mark Santos'
            }),
            'principal': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 text-lg font-mono font-bold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'interest_rate': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'min': '0.00',
                'placeholder': '0.00'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'payment_frequency': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'minimum_payment': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'min': '0.00',
                'placeholder': '0.00'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'rows': 2,
                'placeholder': 'Terms, repayment details, contact info...'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.initial.get('start_date'):
            self.initial['start_date'] = timezone.now().date()

    def clean(self):
        cleaned_data = super().clean()
        s_date = cleaned_data.get('start_date')
        d_date = cleaned_data.get('due_date')
        if s_date and d_date and d_date < s_date:
            self.add_error('due_date', 'Due date cannot be earlier than start date.')
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class DebtPaymentForm(forms.ModelForm):
    create_transaction = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-5 h-5 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700',
            'id': 'id_create_transaction'
        }),
        label="Automatically create linked transaction"
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
            'id': 'id_payment_account'
        }),
        label="Account used for payment"
    )

    class Meta:
        model = DebtPayment
        fields = ('date', 'amount', 'notes')
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 text-lg font-mono font-bold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'notes': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. Monthly installment installment #3'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.debt = kwargs.pop('debt', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()

        if self.user:
            self.fields['account'].queryset = Account.objects.filter(user=self.user, is_active=True)
            first_acc = self.fields['account'].queryset.first()
            if first_acc:
                self.fields['account'].initial = first_acc

    def clean(self):
        cleaned_data = super().clean()
        create_tx = cleaned_data.get('create_transaction')
        account = cleaned_data.get('account')
        if create_tx and not account:
            self.add_error('account', 'Please select an account for the linked transaction.')
        return cleaned_data

    def save(self, commit=True):
        payment = super().save(commit=False)
        if self.debt:
            payment.debt = self.debt

        if commit:
            payment.save()
            # Handle linked transaction creation
            if self.cleaned_data.get('create_transaction') and self.cleaned_data.get('account'):
                account = self.cleaned_data['account']
                # If debt is OWED_BY_ME, paying it is an EXPENSE
                # If debt is OWED_TO_ME, receiving payment is an INCOME
                if self.debt.debt_type == Debt.TYPE_OWED_BY_ME:
                    tx_type = Transaction.TYPE_EXPENSE
                    desc = f"Debt Payment: {self.debt.title} ({self.debt.creditor_or_debtor})"
                    # Category: Debt Payment if exists
                    category = Category.objects.filter(user=self.user, name__icontains='Debt').first()
                else:
                    tx_type = Transaction.TYPE_INCOME
                    desc = f"Debt Collection: {self.debt.title} ({self.debt.creditor_or_debtor})"
                    category = Category.objects.filter(user=self.user, category_type='INCOME').first()

                tx = Transaction.objects.create(
                    user=self.user,
                    transaction_type=tx_type,
                    date=payment.date,
                    amount=payment.amount,
                    account=account,
                    category=category,
                    description=desc,
                    notes=payment.notes or f"Linked payment for debt ID #{self.debt.pk}"
                )
                payment.linked_transaction = tx
                payment.save(update_fields=['linked_transaction'])

        return payment
