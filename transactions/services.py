from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, date
from .models import Transaction

def filter_transactions(user, query_params):
    """
    Filters transactions for user based on GET parameters:
    - date_from (YYYY-MM-DD)
    - date_to (YYYY-MM-DD)
    - type (INCOME, EXPENSE, TRANSFER)
    - account (account ID)
    - category (category ID)
    - q (search string in description or notes)
    """
    qs = Transaction.objects.filter(user=user).select_related('account', 'to_account', 'category')

    date_from = query_params.get('date_from')
    if date_from:
        try:
            qs = qs.filter(date__gte=datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass

    date_to = query_params.get('date_to')
    if date_to:
        try:
            qs = qs.filter(date__lte=datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    tx_type = query_params.get('type')
    if tx_type and tx_type in dict(Transaction.TRANSACTION_TYPES):
        qs = qs.filter(transaction_type=tx_type)

    account_id = query_params.get('account')
    if account_id:
        qs = qs.filter(Q(account_id=account_id) | Q(to_account_id=account_id))

    category_id = query_params.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    q = query_params.get('q')
    if q:
        qs = qs.filter(Q(description__icontains=q) | Q(notes__icontains=q))

    return qs


def calculate_transaction_totals(transactions_qs):
    """
    Returns {total_income, total_expense, net} for a given transaction queryset.
    Transfers are internal and do not count towards income/expense totals.
    """
    income = transactions_qs.filter(transaction_type=Transaction.TYPE_INCOME).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    expense = transactions_qs.filter(transaction_type=Transaction.TYPE_EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    return {
        'income': income,
        'expense': expense,
        'net': income - expense,
    }


def calculate_next_date(current_date, frequency):
    """
    Calculates the subsequent due date based on frequency.
    """
    from datetime import timedelta, date
    import calendar
    from .models import RecurringTransaction

    if frequency == RecurringTransaction.FREQ_DAILY:
        return current_date + timedelta(days=1)
    elif frequency == RecurringTransaction.FREQ_WEEKLY:
        return current_date + timedelta(days=7)
    elif frequency == RecurringTransaction.FREQ_BIWEEKLY:
        return current_date + timedelta(days=14)
    elif frequency == RecurringTransaction.FREQ_MONTHLY:
        y = current_date.year + (current_date.month) // 12
        m = (current_date.month % 12) + 1
        max_d = calendar.monthrange(y, m)[1]
        d = min(current_date.day, max_d)
        return date(y, m, d)
    elif frequency == RecurringTransaction.FREQ_YEARLY:
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            return current_date.replace(year=current_date.year + 1, day=28)
    return current_date + timedelta(days=30)


def record_bill_payment(bill, payment_date=None, notes=None):
    """
    Logs an expense transaction for a recurring bill and rolls the next_run_date forward.
    Returns the created Transaction.
    """
    if payment_date is None:
        payment_date = timezone.now().date()

    tx = Transaction.objects.create(
        user=bill.user,
        transaction_type=bill.transaction_type,
        date=payment_date,
        amount=bill.amount,
        account=bill.account,
        to_account=bill.to_account,
        category=bill.category,
        description=f"{bill.description} (Paid Bill)",
        notes=notes or f"Paid via Monthly Bills tracker. Schedule #{bill.id} ({bill.get_frequency_display()})"
    )

    # Roll forward next_run_date
    next_due = calculate_next_date(bill.next_run_date, bill.frequency)
    bill.next_run_date = next_due
    if bill.end_date and bill.next_run_date > bill.end_date:
        bill.is_active = False
    bill.save()

    return tx


def get_bills_summary(user):
    """
    Returns summarized commitments for user's recurring monthly bills and subscriptions.
    """
    from datetime import timedelta
    import calendar
    from .models import RecurringTransaction

    today = timezone.now().date()
    thirty_days_later = today + timedelta(days=30)
    seven_days_later = today + timedelta(days=7)

    bills = RecurringTransaction.objects.filter(
        user=user
    ).select_related('account', 'category').order_by('next_run_date')

    active_bills = bills.filter(is_active=True)

    # Calculate monthly equivalent commitments
    monthly_commitment = Decimal('0.00')
    for b in active_bills:
        if b.transaction_type == Transaction.TYPE_EXPENSE:
            if b.frequency == RecurringTransaction.FREQ_MONTHLY:
                monthly_commitment += b.amount
            elif b.frequency == RecurringTransaction.FREQ_WEEKLY:
                monthly_commitment += b.amount * Decimal('4.33')
            elif b.frequency == RecurringTransaction.FREQ_BIWEEKLY:
                monthly_commitment += b.amount * Decimal('2.17')
            elif b.frequency == RecurringTransaction.FREQ_YEARLY:
                monthly_commitment += b.amount / Decimal('12')
            elif b.frequency == RecurringTransaction.FREQ_DAILY:
                monthly_commitment += b.amount * Decimal('30')

    # Compute upcoming metrics
    due_in_7_days = active_bills.filter(next_run_date__lte=seven_days_later)
    due_in_30_days = active_bills.filter(next_run_date__lte=thirty_days_later)

    return {
        'all_bills': bills,
        'active_bills': active_bills,
        'monthly_commitment': monthly_commitment.quantize(Decimal('0.01')),
        'total_active_count': active_bills.count(),
        'due_7_days_count': due_in_7_days.count(),
        'due_7_days_sum': sum((b.amount for b in due_in_7_days), Decimal('0.00')),
        'due_30_days_count': due_in_30_days.count(),
        'due_30_days_sum': sum((b.amount for b in due_in_30_days), Decimal('0.00')),
    }

