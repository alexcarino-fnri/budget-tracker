from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.SummaryReportView.as_view(), name='summary'),
    path('export/transactions/csv/', views.ExportTransactionsCSVView.as_view(), name='export_transactions_csv'),
    path('export/transactions/excel/', views.ExportTransactionsExcelView.as_view(), name='export_transactions_excel'),
    path('export/debts/excel/', views.ExportDebtsExcelView.as_view(), name='export_debts_excel'),
    path('import/transactions/', views.ImportTransactionsView.as_view(), name='import'),
]
