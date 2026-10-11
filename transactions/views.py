from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone

from decimal import Decimal
from .models import Transaction, RecurringTransaction
from .forms import TransactionForm, BillForm
from .services import filter_transactions, calculate_transaction_totals, get_bills_summary, record_bill_payment
from wallets.models import Account
from budgets.models import Category


class TransactionListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = 'transactions/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 25

    def get_queryset(self):
        return filter_transactions(self.request.user, self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_filtered = filter_transactions(self.request.user, self.request.GET)
        context['totals'] = calculate_transaction_totals(all_filtered)
        context['user_accounts'] = Account.objects.filter(user=self.request.user, is_active=True)
        from django.db.models import Q
        context['user_categories'] = Category.objects.filter(
            Q(user=self.request.user) | Q(user__isnull=True)
        ).order_by('category_type', 'name')
        context['selected_account'] = self.request.GET.get('account', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['search_q'] = self.request.GET.get('q', '')
        return context

    def render_to_response(self, context, **response_kwargs):
        # HTMX partial swap for responsive search & filters without full page reload
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'transactions/partials/transaction_table.html', context)
        return super().render_to_response(context, **response_kwargs)


class TransactionCreateView(LoginRequiredMixin, CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transactions:list')

    def get_initial(self):
        initial = super().get_initial()
        if 'account' in self.request.GET:
            initial['account'] = self.request.GET.get('account')
        if 'type' in self.request.GET:
            initial['transaction_type'] = self.request.GET.get('type')
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Transaction '{form.instance.description}' recorded successfully.")
        return super().form_valid(form)


class TransactionUpdateView(LoginRequiredMixin, UpdateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'transactions/transaction_form.html'
    success_url = reverse_lazy('transactions:list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Transaction '{form.instance.description}' updated.")
        return super().form_valid(form)


class TransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = Transaction
    template_name = 'transactions/transaction_confirm_delete.html'
    success_url = reverse_lazy('transactions:list')

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user)

    def form_valid(self, form):
        tx = self.get_object()
        desc = tx.description
        messages.success(self.request, f"Transaction '{desc}' deleted.")
        return super().form_valid(form)


from django.views import View
from django.http import JsonResponse
from .ocr_service import parse_receipt_text_to_data
from debts.models import Debt, DebtPayment

class ScanReceiptView(LoginRequiredMixin, View):
    """
    Renders the interactive Smart Receipt Scanner interface or accepts image OCR analysis.
    """
    template_name = 'transactions/scan_receipt.html'

    def get(self, request):
        accounts = Account.objects.filter(user=request.user, is_active=True)
        from django.db.models import Q
        categories = Category.objects.filter(Q(user=request.user) | Q(user__isnull=True)).order_by('name')
        active_debts = Debt.objects.filter(user=request.user, status=Debt.STATUS_ACTIVE)
        
        context = {
            'accounts': accounts,
            'categories': categories,
            'active_debts': active_debts,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """
        Receives OCR text from Tesseract client-side / server-side and analyzes it.
        """
        ocr_text = request.POST.get('ocr_text', '').strip()
        analysis = parse_receipt_text_to_data(ocr_text, request.user)
        return JsonResponse({
            'status': 'success',
            'data': analysis
        })


class ProcessScannedReceiptView(LoginRequiredMixin, View):
    """
    Saves the analyzed receipt as a verified transaction and optionally links it to debt payment.
    """
    def post(self, request):
        amount_raw = request.POST.get('amount')
        date_raw = request.POST.get('date')
        description = request.POST.get('description', 'Scanned Receipt Transaction').strip()
        account_id = request.POST.get('account_id')
        category_id = request.POST.get('category_id')
        transaction_type = request.POST.get('transaction_type', 'EXPENSE')
        notes = request.POST.get('notes', '').strip()
        is_debt_payment = request.POST.get('is_debt_payment') == 'true' or request.POST.get('is_debt_payment') == '1'
        debt_id = request.POST.get('debt_id')
        receipt_image = request.FILES.get('receipt_image')

        try:
            amount = Decimal(amount_raw)
            if amount <= Decimal('0.00'):
                raise ValueError("Amount must be positive.")
        except Exception:
            messages.error(request, "Invalid receipt amount.")
            return redirect('transactions:scan_receipt')

        account = get_object_or_404(Account, pk=account_id, user=request.user)
        category = Category.objects.filter(pk=category_id).first() if category_id else None

        # Create Transaction
        tx = Transaction.objects.create(
            user=request.user,
            transaction_type=transaction_type,
            date=date_raw or timezone.now().date(),
            amount=amount,
            account=account,
            category=category,
            description=description,
            notes=notes,
            receipt=receipt_image
        )

        # If flagged as debt payment, automatically record DebtPayment
        if is_debt_payment and debt_id:
            debt = Debt.objects.filter(pk=debt_id, user=request.user).first()
            if debt:
                DebtPayment.objects.create(
                    debt=debt,
                    date=tx.date,
                    amount=tx.amount,
                    notes=f"Auto-logged from receipt: {tx.description}",
                    linked_transaction=tx
                )
                messages.success(request, f"Receipt logged! Added transaction and applied payment of {account.currency_symbol} {amount} to debt '{debt.title}'.")
                return redirect('debts:detail', pk=debt.pk)

        messages.success(request, f"Receipt successfully recorded into '{account.name}'!")
        return redirect('transactions:list')


class BillListView(LoginRequiredMixin, ListView):
    """
    Dedicated view for Monthly Bills & Subscriptions, separate from Budgets and Goals.
    """
    model = RecurringTransaction
    template_name = 'transactions/bills_list.html'
    context_object_name = 'bills'

    def get_queryset(self):
        qs = RecurringTransaction.objects.filter(
            user=self.request.user
        ).select_related('account', 'category').order_by('next_run_date')

        status_filter = self.request.GET.get('status')
        if status_filter == 'active':
            qs = qs.filter(is_active=True)
        elif status_filter == 'paused':
            qs = qs.filter(is_active=False)

        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(description__icontains=q)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        summary = get_bills_summary(self.request.user)
        context.update(summary)

        # Annotate days remaining on bills in queryset
        annotated_bills = []
        for bill in context['bills']:
            days_left = (bill.next_run_date - today).days
            bill.days_left = days_left
            bill.is_overdue = days_left < 0
            bill.is_due_today = days_left == 0
            bill.is_due_soon = 0 <= days_left <= 7
            annotated_bills.append(bill)

        context['bills'] = annotated_bills
        context['selected_status'] = self.request.GET.get('status', 'all')
        context['search_q'] = self.request.GET.get('q', '')
        return context


class BillCreateView(LoginRequiredMixin, CreateView):
    """
    Create a new recurring monthly bill or subscription.
    """
    model = RecurringTransaction
    form_class = BillForm
    template_name = 'transactions/bill_form.html'
    success_url = reverse_lazy('transactions:bills_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, f"Monthly bill '{form.instance.description}' added to your tracker!")
        return super().form_valid(form)


class BillUpdateView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing monthly bill or subscription schedule.
    """
    model = RecurringTransaction
    form_class = BillForm
    template_name = 'transactions/bill_form.html'
    success_url = reverse_lazy('transactions:bills_list')

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f"Updated monthly bill '{form.instance.description}'!")
        return super().form_valid(form)


class BillDeleteView(LoginRequiredMixin, DeleteView):
    """
    Remove or deactivate a monthly bill schedule.
    """
    model = RecurringTransaction
    template_name = 'transactions/bill_confirm_delete.html'
    success_url = reverse_lazy('transactions:bills_list')

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        messages.success(request, f"Monthly bill '{obj.description}' has been deleted.")
        return super().delete(request, *args, **kwargs)


class BillPayNowView(LoginRequiredMixin, CreateView):
    """
    One-click action to record payment for an upcoming bill and advance the due date to the next cycle.
    """
    def post(self, request, pk, *args, **kwargs):
        bill = get_object_or_404(RecurringTransaction, pk=pk, user=request.user)
        old_due = bill.next_run_date
        tx = record_bill_payment(bill)
        messages.success(
            request, 
            f"Recorded payment of {bill.account.currency_symbol} {tx.amount} for '{bill.description}'! Next due date advanced to {bill.next_run_date}."
        )
        return redirect('transactions:bills_list')


