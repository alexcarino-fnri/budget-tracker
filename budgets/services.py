from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
import calendar
from datetime import date
from .models import Category, Budget
from transactions.models import Transaction

DEFAULT_CATEGORIES_DATA = [
    # Income
    ('Salary', 'INCOME', 'briefcase', '#10b981'),
    ('Freelance', 'INCOME', 'laptop', '#059669'),
    ('Allowance', 'INCOME', 'gift', '#14b8a6'),
    ('Investments', 'INCOME', 'trending-up', '#06b6d4'),
    ('Others (Income)', 'INCOME', 'plus-circle', '#3b82f6'),

    # Expense
    ('Food & Dining', 'EXPENSE', 'utensils', '#f97316'),
    ('Transportation', 'EXPENSE', 'bus', '#0ea5e9'),
    ('Bills & Utilities', 'EXPENSE', 'zap', '#eab308'),
    ('Rent & Housing', 'EXPENSE', 'home', '#6366f1'),
    ('Groceries', 'EXPENSE', 'shopping-cart', '#84cc16'),
    ('Health & Medical', 'EXPENSE', 'heart-pulse', '#ef4444'),
    ('Education', 'EXPENSE', 'graduation-cap', '#8b5cf6'),
    ('Entertainment', 'EXPENSE', 'film', '#ec4899'),
    ('Shopping', 'EXPENSE', 'shopping-bag', '#f43f5e'),
    ('Subscriptions', 'EXPENSE', 'refresh-cw', '#a855f7'),
    ('Debt Payment', 'EXPENSE', 'scale', '#d97706'),
    ('Others (Expense)', 'EXPENSE', 'more-horizontal', '#64748b'),
]

def ensure_default_categories(user):
    """
    Creates default categories for user if user has none.
    """
    if not Category.objects.filter(user=user).exists():
        categories = []
        for name, ctype, icon, color in DEFAULT_CATEGORIES_DATA:
            categories.append(
                Category(
                    user=user,
                    name=name,
                    category_type=ctype,
                    icon=icon,
                    color=color,
                    is_default=True
                )
            )
        Category.objects.bulk_create(categories)


def get_monthly_budget_progress(user, year=None, month=None):
    """
    Calculates spending vs budget for each category in the specified month.
    Warns at 80%, alerts at 100%+.
    """
    now = timezone.now().date()
    if not year:
        year = now.year
    if not month:
        month = now.month

    ensure_default_categories(user)

    budgets = Budget.objects.filter(user=user, year=year, month=month).select_related('category')
    
    # Range of month
    _, last_day = calendar.monthrange(year, month)
    start_date = date(year, month, 1)
    end_date = date(year, month, last_day)

    # Actual spending per category this month
    expenses = Transaction.objects.filter(
        user=user,
        transaction_type=Transaction.TYPE_EXPENSE,
        date__range=[start_date, end_date],
        category__isnull=False
    ).values('category_id').annotate(total_spent=Sum('amount'))

    spent_by_cat = {item['category_id']: (item['total_spent'] or Decimal('0.00')) for item in expenses}

    progress_list = []
    total_budgeted = Decimal('0.00')
    total_spent = Decimal('0.00')

    user_threshold = 80
    if hasattr(user, 'profile') and user.profile.monthly_budget_alert_threshold:
        user_threshold = user.profile.monthly_budget_alert_threshold

    for b in budgets:
        effective_limit = b.amount + (b.rollover_amount if b.rollover_unused else Decimal('0.00'))
        spent = spent_by_cat.get(b.category_id, Decimal('0.00'))
        total_budgeted += effective_limit
        total_spent += spent

        pct = Decimal('0.00')
        if effective_limit > Decimal('0.00'):
            pct = ((spent / effective_limit) * Decimal('100.0')).quantize(Decimal('0.1'))

        remaining = effective_limit - spent

        if pct >= Decimal('100.0'):
            status = 'ALERT'
        elif pct >= Decimal(str(user_threshold)):
            status = 'WARNING'
        else:
            status = 'NORMAL'

        progress_list.append({
            'budget': b,
            'category': b.category,
            'limit': effective_limit,
            'base_amount': b.amount,
            'rollover_amount': b.rollover_amount,
            'spent': spent,
            'remaining': remaining,
            'percentage': min(pct, Decimal('100.0')),
            'raw_percentage': pct,
            'status': status,
        })

    overall_pct = Decimal('0.00')
    if total_budgeted > Decimal('0.00'):
        overall_pct = ((total_spent / total_budgeted) * Decimal('100.0')).quantize(Decimal('0.1'))

    return {
        'items': progress_list,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'total_budgeted': total_budgeted,
        'total_spent': total_spent,
        'total_remaining': total_budgeted - total_spent,
        'overall_percentage': min(overall_pct, Decimal('100.0')),
        'raw_overall_percentage': overall_pct,
    }
