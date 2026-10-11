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
    Returns list of accounts for a user with their dynamically calculated balance attached.
    """
    accounts = Account.objects.filter(user=user, is_active=True)
    account_list = []
    total_assets = Decimal('0.00')
    total_liabilities = Decimal('0.00')

    for acc in accounts:
        bal = get_account_balance(acc)
        acc.current_balance = bal
        account_list.append(acc)
        if acc.account_type == 'CREDIT_CARD':
            # Negative or positive credit balance
            if bal < Decimal('0.00'):
                total_liabilities += abs(bal)
            else:
                total_assets += bal
        else:
            if bal >= Decimal('0.00'):
                total_assets += bal
            else:
                total_liabilities += abs(bal)

    return {
        'accounts': account_list,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_balance': total_assets - total_liabilities,
    }
