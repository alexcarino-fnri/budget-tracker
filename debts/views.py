from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from decimal import Decimal
from .models import Debt, DebtPayment
from .forms import DebtForm, DebtPaymentForm
from .services import get_user_debts_overview, get_debt_summary, compare_payoff_strategies

class DebtListView(LoginRequiredMixin, ListView):
    model = Debt
    template_name = 'debts/debt_list.html'
    context_object_name = 'debts'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        overview = get_user_debts_overview(self.request.user)
        context['i_owe'] = overview['i_owe']
        context['owed_to_me'] = overview['owed_to_me']
        context['total_i_owe'] = overview['total_i_owe']
        context['total_owed_to_me'] = overview['total_owed_to_me']
        context['net_debt_position'] = overview['net_debt_position']
        return context


class DebtDetailView(LoginRequiredMixin, DetailView):
    model = Debt
    template_name = 'debts/debt_detail.html'
    context_object_name = 'debt'

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        debt = self.get_object()
        context['summary'] = get_debt_summary(debt)
        context['payments'] = debt.payments.all().select_related('linked_transaction')
        context['payment_form'] = DebtPaymentForm(user=self.request.user, debt=debt)
        return context


class DebtCreateView(LoginRequiredMixin, CreateView):
    model = Debt
    form_class = DebtForm
    template_name = 'debts/debt_form.html'
    success_url = reverse_lazy('debts:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Debt entry '{form.instance.title}' created.")
        return super().form_valid(form)


class DebtUpdateView(LoginRequiredMixin, UpdateView):
    model = Debt
    form_class = DebtForm
    template_name = 'debts/debt_form.html'
    success_url = reverse_lazy('debts:list')

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Debt entry '{form.instance.title}' updated.")
        return super().form_valid(form)


class DebtDeleteView(LoginRequiredMixin, DeleteView):
    model = Debt
    template_name = 'debts/debt_confirm_delete.html'
    success_url = reverse_lazy('debts:list')

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)

    def form_valid(self, form):
        debt = self.get_object()
        messages.success(self.request, f"Debt entry '{debt.title}' removed.")
        return super().form_valid(form)


class DebtPaymentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        debt = get_object_or_404(Debt, pk=pk, user=request.user)
        form = DebtPaymentForm(request.POST, user=request.user, debt=debt)
        if form.is_valid():
            payment = form.save()
            messages.success(request, f"Recorded payment of {payment.amount} for '{debt.title}'.")
        else:
            messages.error(request, "Failed to record payment. Please check required fields.")
        return redirect('debts:detail', pk=debt.pk)


class DebtPayoffPlannerView(LoginRequiredMixin, View):
    template_name = 'debts/debt_planner.html'

    def get(self, request):
        extra_monthly_raw = request.GET.get('extra', '1000')
        strategy_param = request.GET.get('strategy', 'AVALANCHE').upper()
        if strategy_param not in ['SNOWBALL', 'AVALANCHE', 'DUE_DATE']:
            strategy_param = 'AVALANCHE'

        try:
            extra_monthly = Decimal(extra_monthly_raw)
            if extra_monthly < Decimal('0.00'):
                extra_monthly = Decimal('0.00')
        except:
            extra_monthly = Decimal('1000.00')

        comparison = compare_payoff_strategies(
            request.user, 
            extra_monthly=extra_monthly, 
            selected_strategy=strategy_param
        )

        active_plan = comparison['avalanche']
        if strategy_param == 'SNOWBALL':
            active_plan = comparison['snowball']
        elif strategy_param == 'DUE_DATE':
            active_plan = comparison['due_date']

        context = {
            'comparison': comparison,
            'extra_monthly': extra_monthly,
            'selected_strategy': strategy_param,
            'active_plan': active_plan,
        }
        return render(request, self.template_name, context)

