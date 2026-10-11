from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

CURRENCY_SYMBOLS = {
    'PHP': '₱',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'JPY': '¥',
    'CAD': 'CA$',
    'AUD': 'A$',
    'SGD': 'S$',
    'HKD': 'HK$',
    'CNY': '¥',
}

def global_finance_context(request):
    """
    Provides global financial defaults, app metadata, and live notifications for upcoming dues.
    """
    currency_code = getattr(settings, 'DEFAULT_CURRENCY', 'PHP')
    currency_symbol = getattr(settings, 'DEFAULT_CURRENCY_SYMBOL', '₱')
    current_path = request.path if hasattr(request, 'path') else ''

    notifications = []
    urgent_count = 0

    if hasattr(request, 'user') and request.user.is_authenticated:
        # 0. Resolve user preferred currency
        if hasattr(request.user, 'profile') and request.user.profile.default_currency:
            currency_code = request.user.profile.default_currency.upper()
            currency_symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)
        else:
            first_account = request.user.financial_accounts.filter(is_active=True).first()
            if first_account and first_account.currency:
                currency_code = first_account.currency.upper()
                currency_symbol = CURRENCY_SYMBOLS.get(currency_code, currency_code)

        today = timezone.now().date()
        thirty_days_later = today + timedelta(days=30)

        from core.models import NotificationDismissal
        dismissed_keys = set(
            NotificationDismissal.objects.filter(user=request.user).values_list('notification_key', flat=True)
        )

        # 1. Upcoming Debts (Debts I Owe & Owed to Me with remaining balance)
        from debts.models import Debt
        from debts.services import get_debt_summary

        user_debts = Debt.objects.filter(
            user=request.user
        ).filter(
            due_date__lte=thirty_days_later
        )

        for d in user_debts:
            notif_key = f"debt-{d.id}-{d.due_date}"
            if notif_key in dismissed_keys or f"debt-{d.id}" in dismissed_keys:
                continue

            s = get_debt_summary(d)
            if s['remaining_balance'] > Decimal('0.00'):
                days_left = (d.due_date - today).days
                is_overdue = days_left < 0
                is_urgent = days_left <= 7

                if is_urgent:
                    urgent_count += 1

                if is_overdue:
                    time_desc = f"Overdue by {abs(days_left)} days"
                    tag_type = "danger"
                elif days_left == 0:
                    time_desc = "Due Today!"
                    tag_type = "danger"
                elif days_left == 1:
                    time_desc = "Due Tomorrow"
                    tag_type = "warning"
                else:
                    time_desc = f"Due in {days_left} days"
                    tag_type = "warning" if is_urgent else "info"

                notifications.append({
                    'id': f"debt-{d.id}",
                    'key': notif_key,
                    'type': 'DEBT',
                    'title': d.title,
                    'subtitle': f"{d.get_debt_type_display()} &bull; {d.creditor_or_debtor}",
                    'amount': s['remaining_balance'],
                    'time_desc': time_desc,
                    'due_date': d.due_date,
                    'is_urgent': is_urgent,
                    'tag_type': tag_type,
                    'action_url': f"/debts/{d.id}/",
                    'action_label': 'Pay / Collect'
                })

        # 2. Upcoming Recurring Bills
        from transactions.models import RecurringTransaction
        recurring_bills = RecurringTransaction.objects.filter(
            user=request.user,
            is_active=True,
            next_run_date__lte=thirty_days_later
        ).select_related('account', 'category')

        for r in recurring_bills:
            notif_key = f"recurring-{r.id}-{r.next_run_date}"
            if notif_key in dismissed_keys or f"recurring-{r.id}" in dismissed_keys:
                continue

            days_left = (r.next_run_date - today).days
            is_urgent = days_left <= 7
            if is_urgent:
                urgent_count += 1

            if days_left < 0:
                time_desc = "Pending auto-run"
                tag_type = "warning"
            elif days_left == 0:
                time_desc = "Due Today"
                tag_type = "warning"
            else:
                time_desc = f"Due in {days_left} days"
                tag_type = "warning" if is_urgent else "info"

            notifications.append({
                'id': f"recurring-{r.id}",
                'key': notif_key,
                'type': 'BILL',
                'title': r.description,
                'subtitle': f"Recurring {r.get_frequency_display()} &bull; {r.account.name}",
                'amount': r.amount,
                'time_desc': time_desc,
                'due_date': r.next_run_date,
                'is_urgent': is_urgent,
                'tag_type': tag_type,
                'action_url': "/transactions/bills/",
                'action_label': 'Pay Bill'
            })

        # Sort notifications by due date
        notifications.sort(key=lambda x: x['due_date'])

        bills_due_count = sum(1 for n in notifications if n['type'] == 'BILL')
        debts_due_count = sum(1 for n in notifications if n['type'] == 'DEBT')
    else:
        bills_due_count = 0
        debts_due_count = 0

    return {
        'CURRENCY_SYMBOL': currency_symbol,
        'CURRENCY_CODE': currency_code,
        'CURRENT_PATH': current_path,
        'APP_NAME': 'PisoFlow',
        'notifications': notifications,
        'notifications_count': len(notifications),
        'urgent_notifications_count': urgent_count,
        'bills_due_count': bills_due_count,
        'debts_due_count': debts_due_count,
    }

