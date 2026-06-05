from django.contrib import admin
from userapp.models import User, BankAccount


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['account_number', 'is_registered', 'created_at']
    list_filter = ['is_registered']
    search_fields = ['account_number']
    readonly_fields = ['is_registered', 'created_at']


admin.site.register(User)
