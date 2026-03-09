import os
import django
from decimal import Decimal
from datetime import date

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Budget_Tracker.settings')
django.setup()

from django.contrib.auth.models import User
from Budget_Track.models import PayCycle, Category, Transaction

def populate():
    # Get the first user (assuming you've created one)
    user = User.objects.first()
    if not user:
        print("No user found. Please create a user first (signup or createsuperuser).")
        return

    print(f"Populating data for user: {user.username}")

    # 1. Ensure Pay Cycles exist
    cycle_10, _ = PayCycle.objects.get_or_create(user=user, name="10th of the Month", defaults={'start_day': 10})
    cycle_25, _ = PayCycle.objects.get_or_create(user=user, name="25th of the Month", defaults={'start_day': 25})

    # 2. Ensure Categories exist
    cat_housing, _ = Category.objects.get_or_create(user=user, name="Housing")
    cat_loans, _ = Category.objects.get_or_create(user=user, name="Loans/Bills")
    cat_income, _ = Category.objects.get_or_create(user=user, name="Income")
    cat_savings, _ = Category.objects.get_or_create(user=user, name="Savings")

    # 3. Clear existing transactions for March to avoid duplicates (Optional)
    # Transaction.objects.filter(user=user, date__month=3).delete()

    # --- 10th of the Month Data ---
    data_10 = [
        # Income
        ('Salary', 30000.00, 'INCOME', cat_income, date(2026, 3, 10)),
        ('Initial Savings', 8618.36, 'INCOME', cat_savings, date(2026, 3, 10)),
        # Expenses
        ('Apartment', 4000.00, 'EXPENSE', cat_housing, date(2026, 3, 10)),
        ('CardBank (March 13)', 5260.00, 'EXPENSE', cat_loans, date(2026, 3, 13)),
        ('CardBank (March 20)', 5260.00, 'EXPENSE', cat_loans, date(2026, 3, 20)),
        ('iPhone', 12633.75, 'EXPENSE', cat_loans, date(2026, 3, 10)),
        ('SLoan (March 12)', 2988.73, 'EXPENSE', cat_loans, date(2026, 3, 12)),
    ]

    # --- 25th of the Month Data ---
    data_25 = [
        # Income
        ('Salary', 30000.00, 'INCOME', cat_income, date(2026, 3, 25)),
        ('Carryover Savings', 8475.88, 'INCOME', cat_savings, date(2026, 3, 25)),
        # Expenses
        ('BDO Loan', 9052.13, 'EXPENSE', cat_loans, date(2026, 3, 25)),
        ('CardBank (March 27)', 5260.00, 'EXPENSE', cat_loans, date(2026, 3, 27)),
        ('CardBank (April 6)', 5260.00, 'EXPENSE', cat_loans, date(2026, 4, 6)),
        ('SpayLater (April 5)', 2774.41, 'EXPENSE', cat_loans, date(2026, 4, 5)),
        ('Salmon', 10000.00, 'EXPENSE', cat_loans, date(2026, 3, 25)),
    ]

    for desc, amt, t_type, cat, dt in data_10:
        Transaction.objects.create(
            user=user, description=desc, amount=Decimal(str(amt)),
            type=t_type, category=cat, pay_cycle=cycle_10, date=dt, is_paid=True
        )

    for desc, amt, t_type, cat, dt in data_25:
        Transaction.objects.create(
            user=user, description=desc, amount=Decimal(str(amt)),
            type=t_type, category=cat, pay_cycle=cycle_25, date=dt, is_paid=True
        )

    print("Successfully populated March data!")

if __name__ == "__main__":
    populate()
