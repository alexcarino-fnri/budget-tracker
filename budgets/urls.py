from django.urls import path
from . import views

app_name = 'budgets'

urlpatterns = [
    path('', views.BudgetListView.as_view(), name='list'),
    path('create/', views.BudgetCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.BudgetDeleteView.as_view(), name='delete'),

    # Category endpoints
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
]
