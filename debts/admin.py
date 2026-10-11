from django.contrib import admin
from .models import Debt, DebtPayment

class DebtPaymentInline(admin.TabularInline):
    model = DebtPayment
    extra = 1

@admin.register(Debt)
class DebtAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'debt_type', 'creditor_or_debtor', 'principal', 'interest_rate', 'due_date', 'status')
    list_filter = ('debt_type', 'status', 'payment_frequency')
    search_fields = ('title', 'creditor_or_debtor', 'user__username')
    inlines = [DebtPaymentInline]

@admin.register(DebtPayment)
class DebtPaymentAdmin(admin.ModelAdmin):
    list_display = ('debt', 'date', 'amount', 'linked_transaction', 'created_at')
    list_filter = ('date',)
    search_fields = ('debt__title', 'notes')
