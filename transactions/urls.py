from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    path('', views.TransactionListView.as_view(), name='list'),
    path('create/', views.TransactionCreateView.as_view(), name='create'),
    path('<int:pk>/edit/', views.TransactionUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.TransactionDeleteView.as_view(), name='delete'),
    path('scan-receipt/', views.ScanReceiptView.as_view(), name='scan_receipt'),
    path('scan-receipt/process/', views.ProcessScannedReceiptView.as_view(), name='process_scanned_receipt'),
    # Monthly Bills & Recurring Subscriptions Hub
    path('bills/', views.BillListView.as_view(), name='bills_list'),
    path('bills/create/', views.BillCreateView.as_view(), name='bill_create'),
    path('bills/<int:pk>/edit/', views.BillUpdateView.as_view(), name='bill_update'),
    path('bills/<int:pk>/delete/', views.BillDeleteView.as_view(), name='bill_delete'),
    path('bills/<int:pk>/pay/', views.BillPayNowView.as_view(), name='bill_pay'),
]

