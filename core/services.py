from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
import calendar
from datetime import date, timedelta
from transactions.models import Transaction, RecurringTransaction
from wallets.models import Account
from wallets.services import get_all_accounts_with_balances
from debts.models import Debt
from debts.services import get_debt_summary, get_user_debts_overview
from budgets.models import Category

def get_dashboard_metrics(user):
    """
    Computes all high-level KPIs, upcoming obligations, and chart series for the dashboard.
    """
    today = timezone.now().date()
    current_year = today.year
    current_month = today.month

    # Current month date bounds
    _, last_day = calendar.monthrange(current_year, current_month)
    month_start = date(current_year, current_month, 1)
    month_end = date(current_year, current_month, last_day)

    # 1. Current Month Cash Flow
    current_month_txs = Transaction.objects.filter(
        user=user,
        date__range=[month_start, month_end]
    )

    monthly_income = current_month_txs.filter(
        transaction_type=Transaction.TYPE_INCOME
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    monthly_expense = current_month_txs.filter(
        transaction_type=Transaction.TYPE_EXPENSE
    ).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

    net_cash_flow = monthly_income - monthly_expense

    # 2. Account Balances & Net Worth
    wallets_summary = get_all_accounts_with_balances(user)
    total_assets = wallets_summary['total_assets']
    total_account_liabilities = wallets_summary['total_liabilities']
    net_account_balance = wallets_summary['net_balance']

    # 3. Debts Overview
    debts_overview = get_user_debts_overview(user)
    total_debt_owed = debts_overview['total_i_owe']
    total_owed_to_me = debts_overview['total_owed_to_me']

    # Total Net Worth = Liquid Assets + Receivables (owed to me) - Liabilities (debts owed + credit balances)
    net_worth = (total_assets + total_owed_to_me) - (total_debt_owed + total_account_liabilities)

    # 4. Recent Transactions
    recent_transactions = Transaction.objects.filter(
        user=user
    ).select_related('account', 'to_account', 'category').order_by('-date', '-created_at')[:8]

    # 5. Upcoming Bills & Debt Due Dates (Next 7 and 30 Days)
    thirty_days_later = today + timedelta(days=30)
    upcoming_debts = []
    
    all_debts = Debt.objects.filter(user=user, due_date__range=[today, thirty_days_later])
    for d in all_debts:
        s = get_debt_summary(d)
        if s['remaining_balance'] > Decimal('0.00'):
            d.remaining_balance = s['remaining_balance']
            d.days_left = (d.due_date - today).days
            d.is_within_7_days = d.days_left <= 7
            upcoming_debts.append(d)

    upcoming_recurring_qs = RecurringTransaction.objects.filter(
        user=user,
        is_active=True,
        next_run_date__range=[today, thirty_days_later]
    ).select_related('account', 'category').order_by('next_run_date')
    
    upcoming_recurring = []
    for r in upcoming_recurring_qs:
        r.days_left = (r.next_run_date - today).days
        r.is_within_7_days = r.days_left <= 7
        upcoming_recurring.append(r)

    # 6. Chart 1: Expenses by Category (Doughnut)

    category_expenses = current_month_txs.filter(
        transaction_type=Transaction.TYPE_EXPENSE,
        category__isnull=False
    ).values('category__name', 'category__color').annotate(total=Sum('amount')).order_by('-total')

    chart_cat_labels = []
    chart_cat_data = []
    chart_cat_colors = []
    for item in category_expenses:
        chart_cat_labels.append(item['category__name'])
        chart_cat_data.append(float(item['total']))
        chart_cat_colors.append(item['category__color'] or '#10b981')

    # 7. Chart 2: Income vs Expense last 6 months (Bar)
    chart_months_labels = []
    chart_income_series = []
    chart_expense_series = []

    for i in range(5, -1, -1):
        # Calculate target year/month
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        _, m_last_day = calendar.monthrange(target_year, target_month)
        m_start = date(target_year, target_month, 1)
        m_end = date(target_year, target_month, m_last_day)

        m_txs = Transaction.objects.filter(user=user, date__range=[m_start, m_end])
        inc = m_txs.filter(transaction_type=Transaction.TYPE_INCOME).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
        exp = m_txs.filter(transaction_type=Transaction.TYPE_EXPENSE).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')

        chart_months_labels.append(calendar.month_abbr[target_month])
        chart_income_series.append(float(inc))
        chart_expense_series.append(float(exp))

    # 8. Chart 3: Debt Balance Trend (Line)
    # Track outstanding principal owed minus cumulative payments by month
    chart_debt_labels = []
    chart_debt_series = []
    
    # Calculate historical debt balance at end of each of the past 6 months
    for i in range(5, -1, -1):
        target_month = current_month - i
        target_year = current_year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        _, m_last_day = calendar.monthrange(target_year, target_month)
        m_end = date(target_year, target_month, m_last_day)

        # Debts that started on or before this month end
        debts_up_to = Debt.objects.filter(user=user, debt_type=Debt.TYPE_OWED_BY_ME, start_date__lte=m_end)
        total_p = debts_up_to.aggregate(tot=Sum('principal'))['tot'] or Decimal('0.00')
        # Payments made on or before this month end
        payments_up_to = Debt.objects.filter(user=user, debt_type=Debt.TYPE_OWED_BY_ME).filter(
            payments__date__lte=m_end
        ).aggregate(tot=Sum('payments__amount'))['tot'] or Decimal('0.00')

        debt_at_point = max(Decimal('0.00'), total_p - payments_up_to)
        chart_debt_labels.append(calendar.month_abbr[target_month])
        chart_debt_series.append(float(debt_at_point))

    return {
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'net_cash_flow': net_cash_flow,
        'total_assets': total_assets,
        'total_account_liabilities': total_account_liabilities,
        'total_debt_owed': total_debt_owed,
        'total_owed_to_me': total_owed_to_me,
        'net_worth': net_worth,
        'recent_transactions': recent_transactions,
        'upcoming_debts': upcoming_debts,
        'upcoming_recurring': upcoming_recurring,
        'accounts': wallets_summary['accounts'],
        'charts': {
            'categories': {
                'labels': chart_cat_labels,
                'data': chart_cat_data,
                'colors': chart_cat_colors,
            },
            'cash_flow': {
                'labels': chart_months_labels,
                'income': chart_income_series,
                'expense': chart_expense_series,
            },
            'debt_trend': {
                'labels': chart_debt_labels,
                'data': chart_debt_series,
            }
        }
    }
