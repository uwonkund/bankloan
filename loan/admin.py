from django.contrib import admin
from .models import Loan
@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    search_fields = ['user_id__username', 'loan_type', 'status']
    list_display = ['id', 'user_id', 'loan_type', 'amount', 'interest_rate', 'collateral_type', 'status', 'application_date', 'approved_by']
    list_filter = ['loan_type', 'status', 'collateral_type']


admin.site.site_header = "Bank Loan Management System"
admin.site.site_title = "Loan Dashboard"
admin.site.index_title = "Welcome to Bank Loan Management System"

# Register your models here.
