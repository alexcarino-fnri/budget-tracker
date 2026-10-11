from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from datetime import date, timedelta, datetime
from .models import Debt, DebtPayment
from transactions.models import Transaction

def get_debt_summary(debt: Debt) -> dict:
    """
    Computes real-time payoff progress for a debt.
    """
    total_paid = debt.payments.aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00')
    remaining = max(Decimal('0.00'), debt.principal - total_paid)
    
    pct = Decimal('0.00')
    if debt.principal > Decimal('0.00'):
        pct = min(Decimal('100.0'), ((total_paid / debt.principal) * Decimal('100.0')).quantize(Decimal('0.1')))

    today = timezone.now().date()
    is_overdue = (remaining > Decimal('0.00') and debt.due_date < today)
    
    # Auto-adjust status representation if fully paid
    computed_status = debt.status
    if remaining <= Decimal('0.00'):
        computed_status = Debt.STATUS_PAID
    elif is_overdue:
        computed_status = Debt.STATUS_OVERDUE
    else:
        computed_status = Debt.STATUS_ACTIVE

    return {
        'total_paid': total_paid,
        'remaining_balance': remaining,
        'percent_paid': pct,
        'is_overdue': is_overdue,
        'status': computed_status,
        'days_until_due': (debt.due_date - today).days if remaining > Decimal('0.00') else 0,
    }


def get_user_debts_overview(user):
    """
    Returns aggregated figures for debts I owe vs debts owed to me.
    """
    debts = Debt.objects.filter(user=user)
    i_owe_list = []
    owed_to_me_list = []

    total_i_owe_remaining = Decimal('0.00')
    total_owed_to_me_remaining = Decimal('0.00')
    total_i_owe_paid = Decimal('0.00')
    total_owed_to_me_paid = Decimal('0.00')

    for d in debts:
        summary = get_debt_summary(d)
        d.summary = summary
        if d.debt_type == Debt.TYPE_OWED_BY_ME:
            i_owe_list.append(d)
            total_i_owe_remaining += summary['remaining_balance']
            total_i_owe_paid += summary['total_paid']
        else:
            owed_to_me_list.append(d)
            total_owed_to_me_remaining += summary['remaining_balance']
            total_owed_to_me_paid += summary['total_paid']

    return {
        'i_owe': i_owe_list,
        'owed_to_me': owed_to_me_list,
        'total_i_owe': total_i_owe_remaining,
        'total_owed_to_me': total_owed_to_me_remaining,
        'net_debt_position': total_owed_to_me_remaining - total_i_owe_remaining,
    }


def calculate_payoff_simulation(debts_data, extra_monthly=Decimal('0.00'), strategy='SNOWBALL'):
    """
    Simulates monthly debt payoff with advanced mechanics:
    - Accounts for varying minimum payments and repayment frequencies (MONTHLY, BIWEEKLY, WEEKLY, ONE_TIME).
    - Preserves specific due dates (e.g. 5th, 15th, 30th of month) and days until due.
    - Strategies supported:
        * 'SNOWBALL': lowest balance first
        * 'AVALANCHE': highest interest rate first
        * 'DUE_DATE': earliest upcoming due date first (minimizes late fees / default risk)
    - Generates complete timeline schedule with debt-by-debt payment allocations and payoff milestones.
    """
    import copy

    active_debts = []
    for d in debts_data:
        bal = Decimal(str(d.get('balance', '0.00')))
        if bal > Decimal('0.00'):
            freq = d.get('payment_frequency', 'MONTHLY')
            raw_min = Decimal(str(d.get('min_payment', '0.00')))
            
            # Normalize minimum payment to a monthly equivalent based on frequency
            if raw_min > Decimal('0.00'):
                if freq == 'WEEKLY':
                    monthly_min = (raw_min * Decimal('52') / Decimal('12')).quantize(Decimal('0.01'))
                elif freq == 'BIWEEKLY':
                    monthly_min = (raw_min * Decimal('26') / Decimal('12')).quantize(Decimal('0.01'))
                elif freq == 'ONE_TIME':
                    monthly_min = raw_min
                else:
                    monthly_min = raw_min
            else:
                # Default 2.5% of balance or 500
                monthly_min = max(Decimal('500.00'), (bal * Decimal('0.025')).quantize(Decimal('0.01')))

            due_date_obj = d.get('due_date')
            if isinstance(due_date_obj, str):
                try:
                    due_date_obj = datetime.strptime(due_date_obj, '%Y-%m-%d').date()
                except Exception:
                    due_date_obj = timezone.now().date()
            elif not due_date_obj:
                due_date_obj = timezone.now().date()

            active_debts.append({
                'id': d['id'],
                'title': d['title'],
                'creditor': d.get('creditor', ''),
                'balance': bal,
                'initial_balance': bal,
                'rate': Decimal(str(d.get('rate', '0.00'))),
                'min_payment': monthly_min,
                'raw_min': raw_min,
                'frequency': freq,
                'due_date': due_date_obj,
                'due_day': due_date_obj.day,
                'payoff_month': None,
                'total_interest': Decimal('0.00'),
                'total_principal_paid': Decimal('0.00'),
            })

    if not active_debts:
        return {
            'months': 0,
            'payoff_date': timezone.now().date(),
            'total_interest': Decimal('0.00'),
            'total_paid': Decimal('0.00'),
            'total_initial_debt': Decimal('0.00'),
            'monthly_schedule': [],
            'debt_summaries': [],
            'strategy': strategy
        }

    total_initial_debt = sum(d['initial_balance'] for d in active_debts)

    # Sort prioritization based on strategy
    if strategy == 'SNOWBALL':
        active_debts.sort(key=lambda x: (x['balance'], -x['rate']))
    elif strategy == 'AVALANCHE':
        active_debts.sort(key=lambda x: (x['rate'], -x['balance']), reverse=True)
    elif strategy == 'DUE_DATE':
        # Earliest due date, then highest APR
        active_debts.sort(key=lambda x: (x['due_date'], -x['rate']))

    months = 0
    total_interest_paid = Decimal('0.00')
    max_months = 360  # 30-year safety limit
    current_date = timezone.now().date()
    rollover_snowball = extra_monthly

    monthly_schedule = []
    
    # Run month-by-month simulation
    while any(d['balance'] > Decimal('0.00') for d in active_debts) and months < max_months:
        months += 1
        month_label_year = current_date.year + (current_date.month + months - 2) // 12
        month_label_month = (current_date.month + months - 2) % 12 + 1
        month_date = date(month_label_year, month_label_month, 1)

        month_interest_accrued = Decimal('0.00')
        month_principal_paid = Decimal('0.00')
        freed_min_payment_this_month = Decimal('0.00')

        debt_allocations = []

        # Step 1: Accrue monthly interest
        for d in active_debts:
            if d['balance'] > Decimal('0.00'):
                monthly_rate = (d['rate'] / Decimal('100.0')) / Decimal('12.0')
                interest = (d['balance'] * monthly_rate).quantize(Decimal('0.01'))
                d['balance'] += interest
                d['total_interest'] += interest
                month_interest_accrued += interest
                total_interest_paid += interest

        # Step 2: Pay mandatory minimums
        for d in active_debts:
            if d['balance'] > Decimal('0.00'):
                required_min = min(d['balance'], d['min_payment'])
                d['balance'] -= required_min
                d['total_principal_paid'] += required_min
                month_principal_paid += required_min
                
                paid_total_for_debt = required_min
                
                if d['balance'] <= Decimal('0.00'):
                    d['balance'] = Decimal('0.00')
                    if d['payoff_month'] is None:
                        d['payoff_month'] = months
                    freed_min_payment_this_month += d['min_payment']

                debt_allocations.append({
                    'id': d['id'],
                    'title': d['title'],
                    'min_paid': required_min,
                    'extra_paid': Decimal('0.00'),
                    'total_paid': paid_total_for_debt,
                    'remaining_balance': d['balance'],
                    'is_cleared': d['balance'] == Decimal('0.00')
                })

        # Step 3: Apply extra snowball contribution + previously freed minimums
        available_extra = rollover_snowball
        for alloc in debt_allocations:
            d = next((x for x in active_debts if x['id'] == alloc['id']), None)
            if d and d['balance'] > Decimal('0.00') and available_extra > Decimal('0.00'):
                extra_pay = min(d['balance'], available_extra)
                d['balance'] -= extra_pay
                d['total_principal_paid'] += extra_pay
                available_extra -= extra_pay
                month_principal_paid += extra_pay
                
                alloc['extra_paid'] = extra_pay
                alloc['total_paid'] += extra_pay
                alloc['remaining_balance'] = d['balance']

                if d['balance'] <= Decimal('0.00'):
                    d['balance'] = Decimal('0.00')
                    alloc['is_cleared'] = True
                    if d['payoff_month'] is None:
                        d['payoff_month'] = months
                    freed_min_payment_this_month += d['min_payment']

        # Add freed payments to permanent rollover for subsequent months
        rollover_snowball += freed_min_payment_this_month

        total_month_payment = month_principal_paid
        remaining_portfolio_balance = sum(d['balance'] for d in active_debts)

        # Record schedule point (store first 36 months in full detail for display, plus key milestones)
        if months <= 36 or remaining_portfolio_balance == Decimal('0.00') or months % 6 == 0:
            monthly_schedule.append({
                'month_index': months,
                'date': month_date,
                'interest_paid': month_interest_accrued,
                'principal_paid': month_principal_paid,
                'total_payment': total_month_payment,
                'remaining_balance': remaining_portfolio_balance,
                'allocations': debt_allocations
            })

    # Estimate payoff date by adding months
    payoff_year = current_date.year + (current_date.month + months - 1) // 12
    payoff_month = (current_date.month + months - 1) % 12 + 1
    payoff_date = date(payoff_year, payoff_month, 1)

    # Debt individual payoff milestones summary
    debt_summaries = []
    for d in active_debts:
        m = d['payoff_month'] or months
        p_yr = current_date.year + (current_date.month + m - 1) // 12
        p_mo = (current_date.month + m - 1) % 12 + 1
        d_payoff_date = date(p_yr, p_mo, d['due_day'] if d['due_day'] <= 28 else 28)
        debt_summaries.append({
            'id': d['id'],
            'title': d['title'],
            'creditor': d['creditor'],
            'rate': d['rate'],
            'frequency': d['frequency'],
            'due_date': d['due_date'],
            'due_day': d['due_day'],
            'initial_balance': d['initial_balance'],
            'monthly_min': d['min_payment'],
            'months_to_payoff': m,
            'payoff_date': d_payoff_date,
            'total_interest': d['total_interest'].quantize(Decimal('0.01')),
            'total_paid': (d['initial_balance'] + d['total_interest']).quantize(Decimal('0.01'))
        })

    return {
        'months': months,
        'payoff_date': payoff_date,
        'total_interest': total_interest_paid.quantize(Decimal('0.01')),
        'total_paid': (total_initial_debt + total_interest_paid).quantize(Decimal('0.01')),
        'total_initial_debt': total_initial_debt,
        'monthly_schedule': monthly_schedule,
        'debt_summaries': debt_summaries,
        'strategy': strategy
    }


def compare_payoff_strategies(user, extra_monthly=Decimal('0.00'), selected_strategy=None):
    """
    Compares Snowball, Avalanche, and Earliest Due Date strategies side-by-side
    for all active debts owed by the user, taking into account different repayment
    due dates, frequencies, and minimum amounts.
    """
    debts = Debt.objects.filter(user=user, debt_type=Debt.TYPE_OWED_BY_ME).order_by('due_date')
    debts_data = []
    total_debt_balance = Decimal('0.00')
    total_minimum_monthly = Decimal('0.00')

    today = timezone.now().date()

    for d in debts:
        summary = get_debt_summary(d)
        if summary['remaining_balance'] > Decimal('0.00'):
            total_debt_balance += summary['remaining_balance']
            
            # Normalize min payment for summary
            raw_min = d.minimum_payment or Decimal('0.00')
            if d.payment_frequency == 'WEEKLY':
                norm_min = (raw_min * Decimal('52') / Decimal('12')).quantize(Decimal('0.01'))
            elif d.payment_frequency == 'BIWEEKLY':
                norm_min = (raw_min * Decimal('26') / Decimal('12')).quantize(Decimal('0.01'))
            else:
                norm_min = raw_min

            total_minimum_monthly += norm_min

            days_to_due = (d.due_date - today).days

            debts_data.append({
                'id': d.id,
                'title': d.title,
                'creditor': d.creditor_or_debtor,
                'balance': summary['remaining_balance'],
                'rate': d.interest_rate,
                'min_payment': d.minimum_payment or Decimal('500.00'),
                'payment_frequency': d.payment_frequency,
                'due_date': d.due_date,
                'days_to_due': days_to_due,
            })

    # Run simulations
    snowball_result = calculate_payoff_simulation(debts_data, extra_monthly, strategy='SNOWBALL')
    avalanche_result = calculate_payoff_simulation(debts_data, extra_monthly, strategy='AVALANCHE')
    duedate_result = calculate_payoff_simulation(debts_data, extra_monthly, strategy='DUE_DATE')
    baseline_result = calculate_payoff_simulation(debts_data, Decimal('0.00'), strategy='SNOWBALL')

    interest_saved_avalanche_vs_snowball = max(Decimal('0.00'), snowball_result['total_interest'] - avalanche_result['total_interest'])
    interest_saved_vs_baseline = max(Decimal('0.00'), baseline_result['total_interest'] - avalanche_result['total_interest'])
    months_saved_vs_baseline = max(0, baseline_result['months'] - avalanche_result['months'])

    # Determine recommended strategy
    recommended_strategy = 'AVALANCHE'
    recommendation_reason = "Saves the most money in overall interest by prioritizing high-APR debts first."
    if snowball_result['months'] < avalanche_result['months']:
        recommended_strategy = 'SNOWBALL'
        recommendation_reason = "Clears debts faster to maximize cash flow freedom and immediate relief."

    return {
        'total_debt': total_debt_balance,
        'total_minimum_monthly': total_minimum_monthly,
        'extra_monthly': extra_monthly,
        'debts_count': len(debts_data),
        'debts_data': debts_data,
        'snowball': snowball_result,
        'avalanche': avalanche_result,
        'due_date': duedate_result,
        'baseline': baseline_result,
        'interest_saved': interest_saved_avalanche_vs_snowball,
        'interest_saved_vs_baseline': interest_saved_vs_baseline,
        'months_saved_vs_baseline': months_saved_vs_baseline,
        'recommended_strategy': recommended_strategy,
        'recommendation_reason': recommendation_reason,
        'selected_strategy': selected_strategy or 'AVALANCHE',
    }

