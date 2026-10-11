from django import forms
from .models import Account

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ('name', 'account_type', 'currency', 'opening_balance', 'color_hex', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. BPI Savings, GCash, Physical Cash'
            }),
            'account_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'currency': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'color_hex': forms.TextInput(attrs={
                'type': 'color',
                'class': 'h-10 w-20 rounded-xl cursor-pointer border border-slate-300 dark:border-slate-700 p-1 bg-white dark:bg-slate-800'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk and self.user and hasattr(self.user, 'profile') and self.user.profile.default_currency:
            self.fields['currency'].initial = self.user.profile.default_currency

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance
