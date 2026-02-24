from django.shortcuts import render, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.db.models import Sum
from django.utils import timezone
from django.http import JsonResponse
from .models import Transaction, Category, BudgetGoal
from .forms import TransactionForm, CategoryForm, BudgetGoalForm
import json

class SignUpView(CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('dashboard')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect('dashboard')

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Determine current pay cycle based on date or GET parameter
        today = timezone.now().date()
        default_cycle = '10th' if today.day <= 15 else '25th'
        current_cycle = self.request.GET.get('cycle', default_cycle)
        
        if current_cycle == '10th':
            header_color = 'bg-primary' # Blue
        elif current_cycle == '25th':
            header_color = 'bg-success' # Green
        else:
            header_color = 'bg-secondary' # Gray for Other

        # Filter transactions for the current cycle
        cycle_transactions = Transaction.objects.filter(user=user, pay_cycle=current_cycle)

        # 1. Total Pay Period Income (Income + Carryover logic could be added here, currently just Income)
        total_income = cycle_transactions.filter(type='INCOME').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # 2. Total Bills (Committed) - Expenses for this cycle
        total_bills = cycle_transactions.filter(type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # 3. Disposable Savings (The "Bottom Line")
        disposable_savings = total_income - total_bills

        # Data for Pie Chart (Expenses by Category for current cycle)
        expense_transactions = cycle_transactions.filter(type='EXPENSE')
        category_data = {}
        for t in expense_transactions:
            cat_name = t.category.name if t.category else 'Uncategorized'
            category_data[cat_name] = float(category_data.get(cat_name, 0) + float(t.amount))
        
        # Budget vs Actual (This might span across cycles, but let's keep it consistent with the view)
        budget_goals = BudgetGoal.objects.filter(user=user)
        budget_progress = []
        for goal in budget_goals:
            # Actual expenses for this category in the current cycle
            actual = cycle_transactions.filter(category=goal.category, type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
            budget_progress.append({
                'category': goal.category.name,
                'limit': goal.limit_amount,
                'actual': actual,
                'percent': min((actual / goal.limit_amount) * 100, 100) if goal.limit_amount > 0 else 0
            })

        # Recent Transactions for the table
        recent_transactions = Transaction.objects.filter(user=user).order_by('-date')[:5]
        
        # Categories for the modal
        categories = Category.objects.filter(user=user)

        context.update({
            'current_cycle': current_cycle,
            'header_color': header_color,
            'total_income': total_income,
            'total_bills': total_bills,
            'disposable_savings': disposable_savings,
            'chart_labels': json.dumps(list(category_data.keys())),
            'chart_data': json.dumps(list(category_data.values())),
            'budget_progress': budget_progress,
            'transactions': recent_transactions,
            'categories': categories
        })
        return context

class TransactionAddAjaxView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            type = request.POST.get('type')
            pay_cycle = request.POST.get('pay_cycle')
            date = request.POST.get('date')
            description = request.POST.get('description')
            is_paid = request.POST.get('is_paid') == 'on'

            category = Category.objects.get(id=category_id, user=request.user)
            
            transaction = Transaction.objects.create(
                user=request.user,
                category=category,
                amount=amount,
                type=type,
                pay_cycle=pay_cycle,
                date=date,
                description=description,
                is_paid=is_paid
            )
            return JsonResponse({'status': 'success', 'message': 'Transaction added successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transaction_list.html'
    context_object_name = 'transactions'

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).order_by('-date')

class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'transaction_confirm_delete.html'
    success_url = reverse_lazy('transaction_list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class CategoryCreateView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class CategoryUpdateView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'category_form.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

class BudgetGoalListView(LoginRequiredMixin, ListView):
    model = BudgetGoal
    template_name = 'budget_goal_list.html'
    context_object_name = 'budget_goals'

    def get_queryset(self):
        return BudgetGoal.objects.filter(user=self.request.user)

class BudgetGoalCreateView(LoginRequiredMixin, CreateView):
    model = BudgetGoal
    form_class = BudgetGoalForm
    template_name = 'budget_goal_form.html'
    success_url = reverse_lazy('budget_goal_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class BudgetGoalUpdateView(LoginRequiredMixin, UpdateView):
    model = BudgetGoal
    form_class = BudgetGoalForm
    template_name = 'budget_goal_form.html'
    success_url = reverse_lazy('budget_goal_list')

    def get_queryset(self):
        return BudgetGoal.objects.filter(user=self.request.user)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        return form

class BudgetGoalDeleteView(LoginRequiredMixin, DeleteView):
    model = BudgetGoal
    template_name = 'budget_goal_confirm_delete.html'
    success_url = reverse_lazy('budget_goal_list')

    def get_queryset(self):
        return BudgetGoal.objects.filter(user=self.request.user)
