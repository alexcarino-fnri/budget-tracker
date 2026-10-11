from django.contrib import admin
from .models import Account

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_type', 'currency', 'opening_balance', 'is_active', 'created_at')
    list_filter = ('account_type', 'is_active', 'currency')
    search_fields = ('name', 'user__username')
