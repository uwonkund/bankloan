from django.contrib import admin
from .models import Payment, PaymentSchedule, Penalty

# Register your models here.
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'schedule', 'amount_paid', 'payment_method', 'status', 'payment_date']
    search_fields = ['loan__loan_type']
    list_filter = ['payment_date', 'payment_method', 'status']
admin.site.site_header = "Bank Loan Management System"
admin.site.site_title = "Payment Dashboard"
admin.site.index_title = "Welcome to Bank Loan Management System"

@admin.register(PaymentSchedule)
class PaymentScheduleAdmin(admin.ModelAdmin):
    list_display = ['id', 'loan', 'due_date', 'amount_due']
    search_fields = ['loan__loan_type']
    list_filter = ['due_date']
admin.site.site_header = "Bank Loan Management System"
admin.site.site_title = "Payment Schedule Dashboard"
admin.site.index_title = "Welcome to Bank Loan Management System"

@admin.register(Penalty)
class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['id', 'schedule', 'penalty_type', 'total_amount_due', 'status', 'applied_at']
    search_fields = ['penalty_type', 'schedule__month_number']
    list_filter = ['status', 'penalty_type', 'applied_at']
admin.site.site_header = "Bank Loan Management System"
admin.site.site_title = "Penalty Dashboard"
admin.site.index_title = "Welcome to Bank Loan Management System"   
# Register your models here.
