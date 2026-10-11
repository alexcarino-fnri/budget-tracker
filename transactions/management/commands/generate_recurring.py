from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta, date
import calendar
from transactions.models import Transaction, RecurringTransaction
from transactions.services import calculate_next_date

class Command(BaseCommand):
    help = 'Processes all due recurring transactions and logs them into the transaction ledger.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        due_entries = RecurringTransaction.objects.filter(
            is_active=True,
            next_run_date__lte=today
        ).select_related('user', 'account', 'to_account', 'category')

        created_count = 0

        for item in due_entries:
            while item.next_run_date <= today and item.is_active:
                # Check end_date
                if item.end_date and item.next_run_date > item.end_date:
                    item.is_active = False
                    item.save()
                    break

                # Create the transaction
                Transaction.objects.create(
                    user=item.user,
                    transaction_type=item.transaction_type,
                    date=item.next_run_date,
                    amount=item.amount,
                    account=item.account,
                    to_account=item.to_account,
                    category=item.category,
                    description=f"{item.description} (Auto)",
                    notes=f"Generated from recurring schedule #{item.id} ({item.frequency})"
                )
                created_count += 1

                # Advance next_run_date
                next_date = calculate_next_date(item.next_run_date, item.frequency)
                item.next_run_date = next_date

                if item.end_date and item.next_run_date > item.end_date:
                    item.is_active = False

                item.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully generated {created_count} recurring transactions.'))


    def calculate_next_date(self, current_date, frequency):
        if frequency == RecurringTransaction.FREQ_DAILY:
            return current_date + timedelta(days=1)
        elif frequency == RecurringTransaction.FREQ_WEEKLY:
            return current_date + timedelta(days=7)
        elif frequency == RecurringTransaction.FREQ_BIWEEKLY:
            return current_date + timedelta(days=14)
        elif frequency == RecurringTransaction.FREQ_MONTHLY:
            # Add one month safely
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
