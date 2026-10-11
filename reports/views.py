from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.utils import timezone
import json

from .services import (
    get_monthly_report_data,
    get_yearly_report_data,
    export_transactions_csv_response,
    export_transactions_excel_response,
    export_debts_excel_response,
    parse_and_validate_csv_file,
    commit_imported_transactions
)

class SummaryReportView(LoginRequiredMixin, View):
    template_name = 'reports/summary_report.html'

    def get(self, request):
        today = timezone.now().date()
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        mode = request.GET.get('mode', 'monthly')  # 'monthly' or 'yearly'

        if mode == 'yearly':
            report_data = get_yearly_report_data(request.user, year)
        else:
            report_data = get_monthly_report_data(request.user, year, month)

        context = {
            'mode': mode,
            'year': year,
            'month': month,
            'report': report_data,
            'years': list(range(today.year - 3, today.year + 2)),
            'months': [(i, timezone.datetime(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        }
        return render(request, self.template_name, context)


class ExportTransactionsCSVView(LoginRequiredMixin, View):
    def get(self, request):
        return export_transactions_csv_response(request.user)


class ExportTransactionsExcelView(LoginRequiredMixin, View):
    def get(self, request):
        return export_transactions_excel_response(request.user)


class ExportDebtsExcelView(LoginRequiredMixin, View):
    def get(self, request):
        return export_debts_excel_response(request.user)


class ImportTransactionsView(LoginRequiredMixin, View):
    template_name = 'reports/import_transactions.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        # Action 1: Upload file and preview
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            if not csv_file.name.endswith('.csv'):
                messages.error(request, "Please upload a valid .csv file.")
                return render(request, self.template_name)

            try:
                result = parse_and_validate_csv_file(request.user, csv_file)
                # Store valid rows in session for preview confirmation
                request.session['csv_import_valid_rows'] = result['valid_rows']
                context = {
                    'preview': True,
                    'result': result,
                }
                return render(request, self.template_name, context)
            except Exception as e:
                messages.error(request, f"Error reading CSV file: {str(e)}")
                return render(request, self.template_name)

        # Action 2: User confirms valid rows after preview
        elif 'confirm_import' in request.POST:
            valid_rows = request.session.get('csv_import_valid_rows', [])
            if not valid_rows:
                messages.error(request, "No pending valid transactions to import.")
                return redirect('reports:import')

            saved_count = commit_imported_transactions(request.user, valid_rows)
            # Clear session
            request.session.pop('csv_import_valid_rows', None)
            messages.success(request, f"Successfully imported {saved_count} transactions!")
            return redirect('transactions:list')

        return render(request, self.template_name)
