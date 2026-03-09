from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, CreateView, UpdateView, DeleteView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from .models import Transaction, Category, BudgetGoal, PayCycle, UserProfile
from .forms import TransactionForm, CategoryForm, BudgetGoalForm, StyledUserCreationForm, PayCycleForm, UserUpdateForm, UserProfileForm
import json
from datetime import timedelta

class SignUpView(CreateView):
    form_class = StyledUserCreationForm
    success_url = reverse_lazy('dashboard')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        user = form.save()
        PayCycle.objects.create(user=user, name="10th of the Month", start_day=10)
        PayCycle.objects.create(user=user, name="25th of the Month", start_day=25)
        UserProfile.objects.create(user=user)
        login(self.request, user)
        return redirect('dashboard')

class ProfileView(LoginRequiredMixin, View):
    template_name = 'profile.html'

    def get(self, request):
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

    def post(self, request):
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('profile')
        return render(request, self.template_name, {
            'user_form': user_form,
            'profile_form': profile_form
        })

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        
        pay_cycles = PayCycle.objects.filter(user=user)
        if not pay_cycles.exists():
            PayCycle.objects.create(user=user, name="10th of the Month", start_day=10)
            PayCycle.objects.create(user=user, name="25th of the Month", start_day=25)
            pay_cycles = PayCycle.objects.filter(user=user)

        today = timezone.now().date()
        current_cycle_id = self.request.GET.get('cycle')
        current_cycle = None
        if current_cycle_id and current_cycle_id.isdigit():
            current_cycle = pay_cycles.filter(id=int(current_cycle_id)).first()
        if not current_cycle:
            current_cycle = pay_cycles.filter(start_day__lte=today.day).last() or pay_cycles.last()

        # --- Notifications Logic ---
        # Find unpaid bills due in the next 7 days
        upcoming_bills = Transaction.objects.filter(
            user=user, 
            type='EXPENSE', 
            is_paid=False, 
            due_date__lte=today + timedelta(days=7),
            due_date__gte=today
        ).order_by('due_date')

        overdue_bills = Transaction.objects.filter(
            user=user, 
            type='EXPENSE', 
            is_paid=False, 
            due_date__lt=today
        ).order_by('due_date')

        # --- Analytics Logic ---
        cycle_transactions = Transaction.objects.filter(user=user, pay_cycle=current_cycle)
        
        salary = cycle_transactions.filter(type='INCOME').exclude(category__name__icontains='Savings').aggregate(Sum('amount'))['amount__sum'] or 0
        savings_carryover = cycle_transactions.filter(type='INCOME', category__name__icontains='Savings').aggregate(Sum('amount'))['amount__sum'] or 0
        total_money = salary + savings_carryover
        total_bills = cycle_transactions.filter(type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
        remaining_savings = salary - total_bills
        
        savings_rate = (remaining_savings / salary * 100) if salary > 0 else 0
        
        six_months_ago = today - timedelta(days=180)
        monthly_data = Transaction.objects.filter(user=user, date__gte=six_months_ago, type='EXPENSE') \
            .annotate(month=TruncMonth('date')) \
            .values('month') \
            .annotate(total=Sum('amount')) \
            .order_by('month')
        
        trend_labels = [d['month'].strftime('%b') for d in monthly_data]
        trend_values = [float(d['total']) for d in monthly_data]

        expense_transactions = cycle_transactions.filter(type='EXPENSE')
        category_data = {}
        for t in expense_transactions:
            cat_name = t.category.name if t.category else 'Uncategorized'
            category_data[cat_name] = float(category_data.get(cat_name, 0) + float(t.amount))
        
        budget_goals = BudgetGoal.objects.filter(user=user)
        budget_progress = []
        for goal in budget_goals:
            actual = cycle_transactions.filter(category=goal.category, type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or 0
            status = 'safe'
            if actual > goal.limit_amount: status = 'danger'
            elif actual > goal.limit_amount * 0.8: status = 'warning'
            
            budget_progress.append({
                'category': goal.category.name,
                'limit': goal.limit_amount,
                'actual': actual,
                'percent': min((actual / goal.limit_amount) * 100, 100) if goal.limit_amount > 0 else 0,
                'status': status
            })

        context.update({
            'profile': profile,
            'current_cycle': current_cycle,
            'pay_cycles': pay_cycles,
            'salary': salary,
            'savings_carryover': savings_carryover,
            'total_money': total_money,
            'total_bills': total_bills,
            'remaining_savings': remaining_savings,
            'savings_rate': round(savings_rate, 1),
            'trend_labels': json.dumps(trend_labels),
            'trend_values': json.dumps(trend_values),
            'chart_labels': json.dumps(list(category_data.keys())),
            'chart_data': json.dumps(list(category_data.values())),
            'budget_progress': budget_progress,
            'upcoming_bills': upcoming_bills,
            'overdue_bills': overdue_bills,
            'transactions': Transaction.objects.filter(user=user).order_by('-date')[:8],
            'categories': Category.objects.filter(user=user)
        })
        return context

# Pay Cycle CRUD
class PayCycleListView(LoginRequiredMixin, ListView):
    model = PayCycle
    template_name = 'pay_cycle_list.html'
    context_object_name = 'pay_cycles'
    def get_queryset(self):
        return PayCycle.objects.filter(user=self.request.user)

class PayCycleCreateView(LoginRequiredMixin, CreateView):
    model = PayCycle
    form_class = PayCycleForm
    template_name = 'pay_cycle_form.html'
    success_url = reverse_lazy('pay_cycle_list')
    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

class PayCycleUpdateView(LoginRequiredMixin, UpdateView):
    model = PayCycle
    form_class = PayCycleForm
    template_name = 'pay_cycle_form.html'
    success_url = reverse_lazy('pay_cycle_list')
    def get_queryset(self):
        return PayCycle.objects.filter(user=self.request.user)

class PayCycleDeleteView(LoginRequiredMixin, DeleteView):
    model = PayCycle
    template_name = 'pay_cycle_confirm_delete.html'
    success_url = reverse_lazy('pay_cycle_list')
    def get_queryset(self):
        return PayCycle.objects.filter(user=self.request.user)

# Transaction Views
class TransactionAddAjaxView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        try:
            category_id = request.POST.get('category')
            amount = request.POST.get('amount')
            type = request.POST.get('type')
            pay_cycle_id = request.POST.get('pay_cycle')
            date = request.POST.get('date')
            due_date = request.POST.get('due_date')
            description = request.POST.get('description')
            is_paid = request.POST.get('is_paid') == 'on'

            category = Category.objects.get(id=category_id, user=request.user)
            pay_cycle = PayCycle.objects.get(id=pay_cycle_id, user=request.user)
            
            transaction = Transaction.objects.create(
                user=request.user,
                category=category,
                amount=amount,
                type=type,
                pay_cycle=pay_cycle,
                date=date,
                due_date=due_date if due_date else None,
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
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
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
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'transaction_confirm_delete.html'
    success_url = reverse_lazy('transaction_list')
    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

# Category Views
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

# Budget Goal Views
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
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
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
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

class BudgetGoalDeleteView(LoginRequiredMixin, DeleteView):
    model = BudgetGoal
    template_name = 'budget_goal_confirm_delete.html'
    success_url = reverse_lazy('budget_goal_list')
    def get_queryset(self):
        return BudgetGoal.objects.filter(user=self.request.user)
