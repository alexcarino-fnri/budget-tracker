from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Account
from .forms import AccountForm
from .services import get_all_accounts_with_balances, get_account_balance
from transactions.models import Transaction

class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'wallets/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        summary = get_all_accounts_with_balances(self.request.user)
        selected_type = self.request.GET.get('type', 'ALL').upper()

        if selected_type != 'ALL':
            if selected_type == 'SAVINGS':
                accounts_shown = [acc for acc in summary['accounts'] if acc.account_type in ('SAVINGS', 'BANK')]
            else:
                accounts_shown = [acc for acc in summary['accounts'] if acc.account_type == selected_type]
        else:
            accounts_shown = summary['accounts']

        context['accounts_with_balances'] = accounts_shown
        context['selected_type'] = selected_type
        context['total_assets'] = summary['total_assets']
        context['total_liabilities'] = summary['total_liabilities']
        context['net_balance'] = summary['net_balance']
        context['credit_card_summary'] = summary['credit_card_summary']
        context['category_counts'] = summary['category_counts']

        # Determine currency symbol for summary cards
        currencies = set(acc.currency for acc in summary['accounts'])
        if len(currencies) == 1:
            code = list(currencies)[0].upper()
            context['primary_currency_symbol'] = Account.CURRENCY_SYMBOLS.get(code, code)
            context['primary_currency_code'] = code
        elif hasattr(self.request.user, 'profile') and self.request.user.profile.default_currency:
            code = self.request.user.profile.default_currency.upper()
            context['primary_currency_symbol'] = Account.CURRENCY_SYMBOLS.get(code, code)
            context['primary_currency_code'] = code
        return context


class AccountCreateView(LoginRequiredMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'wallets/account_form.html'
    success_url = reverse_lazy('wallets:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        account = form.save()
        # If user only has this currency or profile default is default PHP, align profile default currency
        if hasattr(self.request.user, 'profile'):
            total_accounts = Account.objects.filter(user=self.request.user).count()
            if total_accounts <= 1:
                self.request.user.profile.default_currency = account.currency
                self.request.user.profile.save(update_fields=['default_currency'])
        messages.success(self.request, f"Account '{account.name}' successfully created.")
        return redirect(self.success_url)


class AccountUpdateView(LoginRequiredMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'wallets/account_form.html'
    success_url = reverse_lazy('wallets:list')

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Account '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = Account
    template_name = 'wallets/account_confirm_delete.html'
    success_url = reverse_lazy('wallets:list')

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def form_valid(self, form):
        account = self.get_object()
        # Check if account has transactions
        has_tx = Transaction.objects.filter(account=account).exists() or Transaction.objects.filter(to_account=account).exists()
        if has_tx:
            messages.error(self.request, f"Cannot delete '{account.name}' because it contains transaction records. Archive or deactivate it instead.")
            return redirect('wallets:list')
        messages.success(self.request, f"Account '{account.name}' removed.")
        return super().form_valid(form)


class AccountDetailView(LoginRequiredMixin, DetailView):
    model = Account
    template_name = 'wallets/account_detail.html'
    context_object_name = 'account'

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_object()
        context['current_balance'] = get_account_balance(account)
        from django.db.models import Q
        context['transactions'] = Transaction.objects.filter(
            Q(account=account) | Q(to_account=account),
            user=self.request.user
        ).order_by('-date', '-created_at')[:30]
        return context
