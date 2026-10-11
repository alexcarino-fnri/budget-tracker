from django.contrib import admin
from .models import Transaction, RecurringTransaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'transaction_type', 'amount', 'account', 'to_account', 'category', 'description')
    list_filter = ('transaction_type', 'date', 'account')
    search_fields = ('description', 'notes', 'user__username')
    date_hierarchy = 'date'

@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'user', 'frequency', 'amount', 'account', 'next_run_date', 'is_active')
    list_filter = ('frequency', 'is_active')
    search_fields = ('description', 'user__username')
