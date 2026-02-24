"""
URL configuration for Budget_Tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from Budget_Track.views import (
    DashboardView, SignUpView, 
    TransactionListView, TransactionCreateView, TransactionUpdateView, TransactionDeleteView, TransactionAddAjaxView,
    CategoryListView, CategoryCreateView, CategoryUpdateView, CategoryDeleteView,
    BudgetGoalListView, BudgetGoalCreateView, BudgetGoalUpdateView, BudgetGoalDeleteView
)

urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Transactions
    path('transactions/', TransactionListView.as_view(), name='transaction_list'),
    path('transactions/add/', TransactionCreateView.as_view(), name='transaction_add'),
    path('transactions/add/ajax/', TransactionAddAjaxView.as_view(), name='transaction_add_ajax'),
    path('transactions/<int:pk>/edit/', TransactionUpdateView.as_view(), name='transaction_edit'),
    path('transactions/<int:pk>/delete/', TransactionDeleteView.as_view(), name='transaction_delete'),

    # Categories
    path('categories/', CategoryListView.as_view(), name='category_list'),
    path('categories/add/', CategoryCreateView.as_view(), name='category_add'),
    path('categories/<int:pk>/edit/', CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name='category_delete'),

    # Budget Goals
    path('budget-goals/', BudgetGoalListView.as_view(), name='budget_goal_list'),
    path('budget-goals/add/', BudgetGoalCreateView.as_view(), name='budget_goal_add'),
    path('budget-goals/<int:pk>/edit/', BudgetGoalUpdateView.as_view(), name='budget_goal_edit'),
    path('budget-goals/<int:pk>/delete/', BudgetGoalDeleteView.as_view(), name='budget_goal_delete'),
]
