from django.urls import path
from . import views

app_name = 'debts'

urlpatterns = [
    path('', views.DebtListView.as_view(), name='list'),
    path('planner/', views.DebtPayoffPlannerView.as_view(), name='planner'),
    path('create/', views.DebtCreateView.as_view(), name='create'),
    path('<int:pk>/', views.DebtDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.DebtUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.DebtDeleteView.as_view(), name='delete'),
    path('<int:pk>/payments/add/', views.DebtPaymentCreateView.as_view(), name='payment_add'),
]
