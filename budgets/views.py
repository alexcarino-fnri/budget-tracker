from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from .models import Budget, Category
from .forms import BudgetForm, CategoryForm
from .services import get_monthly_budget_progress, ensure_default_categories

class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'budgets/budget_list.html'
    context_object_name = 'budgets'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now().date()
        year = int(self.request.GET.get('year', now.year))
        month = int(self.request.GET.get('month', now.month))

        progress = get_monthly_budget_progress(self.request.user, year=year, month=month)
        context['progress_data'] = progress
        context['selected_year'] = year
        context['selected_month'] = month
        context['years'] = list(range(now.year - 2, now.year + 3))
        context['months'] = [(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)]

        from django.db.models import Q
        context['categories'] = Category.objects.filter(
            Q(user=self.request.user) | Q(user__isnull=True)
        ).order_by('category_type', 'name')
        return context


class BudgetCreateView(LoginRequiredMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'budgets/budget_form.html'
    success_url = reverse_lazy('budgets:list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # Prevent duplicate budget for same category/month/year
        existing = Budget.objects.filter(
            user=self.request.user,
            category=form.cleaned_data['category'],
            year=form.cleaned_data['year'],
            month=form.cleaned_data['month']
        ).first()
        if existing:
            existing.amount = form.cleaned_data['amount']
            existing.rollover_unused = form.cleaned_data['rollover_unused']
            existing.save()
            messages.success(self.request, f"Updated existing budget for {existing.category.name}.")
            return redirect(self.success_url)

        messages.success(self.request, f"Budget for {form.instance.category.name} created.")
        return super().form_valid(form)


class BudgetUpdateView(LoginRequiredMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'budgets/budget_form.html'
    success_url = reverse_lazy('budgets:list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Budget for {form.instance.category.name} updated.")
        return super().form_valid(form)


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = 'budgets/budget_confirm_delete.html'
    success_url = reverse_lazy('budgets:list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def form_valid(self, form):
        b = self.get_object()
        cat_name = b.category.name
        messages.success(self.request, f"Budget for '{cat_name}' removed.")
        return super().form_valid(form)


# Category Management Views
class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'budgets/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        from django.db.models import Q
        ensure_default_categories(self.request.user)
        return Category.objects.filter(
            Q(user=self.request.user) | Q(user__isnull=True)
        ).order_by('category_type', 'name')


class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'budgets/category_form.html'
    success_url = reverse_lazy('budgets:categories')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' created.")
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'budgets/category_form.html'
    success_url = reverse_lazy('budgets:categories')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' updated.")
        return super().form_valid(form)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'budgets/category_confirm_delete.html'
    success_url = reverse_lazy('budgets:categories')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def form_valid(self, form):
        cat = self.get_object()
        # Verify if used in transactions
        from transactions.models import Transaction
        if Transaction.objects.filter(category=cat).exists():
            messages.error(self.request, f"Cannot delete category '{cat.name}' because it is linked to transactions.")
            return redirect('budgets:categories')
        messages.success(self.request, f"Category '{cat.name}' deleted.")
        return super().form_valid(form)
