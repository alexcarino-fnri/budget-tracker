from django.contrib import admin
from .models import Category, Budget

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_type', 'user', 'icon', 'color', 'is_default')
    list_filter = ('category_type', 'is_default')
    search_fields = ('name', 'user__username')

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'user', 'month', 'year', 'amount', 'rollover_unused', 'rollover_amount')
    list_filter = ('year', 'month', 'rollover_unused')
    search_fields = ('category__name', 'user__username')
