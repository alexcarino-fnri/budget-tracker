from django import forms
from django.utils import timezone
from .models import Category, Budget

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'category_type', 'icon', 'color')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. Coffee & Snacks, Gym, Pet Supplies'
            }),
            'category_type': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'placeholder': 'e.g. coffee, heart, tag, car, home'
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'h-10 w-20 rounded-xl cursor-pointer border border-slate-300 dark:border-slate-700 p-1 bg-white dark:bg-slate-800'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance


class BudgetForm(forms.ModelForm):
    MONTH_CHOICES = [(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
        })
    )

    class Meta:
        model = Budget
        fields = ('category', 'month', 'year', 'amount', 'rollover_unused')
        widgets = {
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition'
            }),
            'year': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'min': '2020',
                'max': '2050'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-2.5 text-lg font-mono font-bold rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:ring-2 focus:ring-emerald-500 outline-none transition',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'rollover_unused': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 dark:border-slate-700'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        now = timezone.now().date()
        if not self.initial.get('month'):
            self.initial['month'] = now.month
        if not self.initial.get('year'):
            self.initial['year'] = now.year

        if self.user:
            from django.db.models import Q
            # Only expense categories can have budgets
            self.fields['category'].queryset = Category.objects.filter(
                Q(user=self.user) | Q(user__isnull=True),
                category_type='EXPENSE'
            ).order_by('name')

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.user = self.user
        if commit:
            instance.save()
        return instance
