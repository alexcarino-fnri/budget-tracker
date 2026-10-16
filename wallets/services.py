from decimal import Decimal
from django.db.models import Sum
from .models import Account

def get_account_balance(account: Account) -> Decimal:
    """
    Computes current real-time balance of an account from transactions:
    current_balance = opening_balance + income - expense + transfers_in - transfers_out
    """
    # Outgoing: EXPENSE or TRANSFER where account is sender
    out_income = Decimal('0.00')
    out_expense = Decimal('0.00')
    transfers_out = Decimal('0.00')

    from transactions.models import Transaction

    outgoing = Transaction.objects.filter(account=account).values('transaction_type').annotate(total=Sum('amount'))
    for item in outgoing:
        ttype = item['transaction_type']
        tot = item['total'] or Decimal('0.00')
        if ttype == Transaction.TYPE_INCOME:
            # An income transaction logged against this account increases it
            out_income += tot
        elif ttype == Transaction.TYPE_EXPENSE:
            out_expense += tot
        elif ttype == Transaction.TYPE_TRANSFER:
            transfers_out += tot

    # Incoming: TRANSFER where to_account is this account
    incoming_transfers = Transaction.objects.filter(
        to_account=account,
        transaction_type=Transaction.TYPE_TRANSFER
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    return (account.opening_balance + out_income - out_expense - transfers_out + incoming_transfers).quantize(Decimal('0.01'))


def get_all_accounts_with_balances(user):
    """
    Returns list of accounts for a user with their dynamically calculated balance attached,
    along with credit card specific metrics (limit, unbilled, available credit, utilization).
    """
    accounts = Account.objects.filter(user=user, is_active=True)
    account_list = []
    total_assets = Decimal('0.00')
    total_liabilities = Decimal('0.00')

    # Credit card aggregates
    total_credit_limit = Decimal('0.00')
    total_available_credit = Decimal('0.00')
    total_unbilled = Decimal('0.00')
    total_credit_debt = Decimal('0.00')

    # Category counts
    category_counts = {
        'ALL': 0,
        'SAVINGS': 0,
        'E_WALLET': 0,
        'CREDIT_CARD': 0,
        'TIME_DEPOSIT': 0,
        'CASH': 0,
        'INVESTMENT': 0,
        'CHECKING': 0,
        'OTHER': 0,
    }

    for acc in accounts:
        bal = get_account_balance(acc)
        acc.current_balance = bal
        account_list.append(acc)

        category_counts['ALL'] += 1
        cat_key = acc.account_type
        if cat_key in category_counts:
            category_counts[cat_key] += 1
        elif cat_key == 'BANK':
            category_counts['SAVINGS'] += 1
        else:
            category_counts['OTHER'] += 1

        if acc.is_credit_card:
            outstanding = acc.total_outstanding_credit
            total_liabilities += outstanding
            total_credit_debt += outstanding
            if acc.credit_limit:
                total_credit_limit += acc.credit_limit
                total_available_credit += acc.remaining_credit
            total_unbilled += acc.total_unbilled
        else:
            if bal >= Decimal('0.00'):
                total_assets += bal
            else:
                total_liabilities += abs(bal)

    overall_utilization = Decimal('0.0')
    if total_credit_limit > Decimal('0.00'):
        overall_utilization = min(Decimal('100.0'), ((total_credit_debt / total_credit_limit) * 100).quantize(Decimal('0.1')))

    return {
        'accounts': account_list,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_balance': total_assets - total_liabilities,
        'credit_card_summary': {
            'total_limit': total_credit_limit,
            'available_credit': total_available_credit,
            'total_unbilled': total_unbilled,
            'total_debt': total_credit_debt,
            'utilization': overall_utilization,
            'has_cards': category_counts['CREDIT_CARD'] > 0,
        },
        'category_counts': category_counts,
    }
