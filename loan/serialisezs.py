from rest_framework import serializers
from .models import Loan

class LoanSerializer(serializers.ModelSerializer):
    # Display the readable labels for choice fields in GET requests (optional but highly recommended)
    loan_type_label = serializers.CharField(source='get_loan_type_display', read_only=True)
    collateral_type_label = serializers.CharField(source='get_collateral_type_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Loan
        fields = [
            'id',
            'user_id',
            'approved_by',
            'loan_type',
            'loan_type_label',
            'amount',
            'interest_rate',
            'annual_interest_amount',
            'total_repayment_amount',
            'monthly_payment',
            'collateral_type',
            'collateral_type_label',
            'collateral_description',
            'application_date',
            'approval_date',
            'status',
            'status_label',
            'created_at',
        ]
        
        # Protect fields that are auto-calculated or managed strictly by the system/admin
        read_only_fields = [
            'id',
            'user_id',                 # Typically set automatically in the View via request.user
            'approved_by',             # Set by admin/bank staff only
            'annual_interest_amount',  # Calculated in model save()
            'total_repayment_amount',  # Calculated in model save()
            'monthly_payment',         # Calculated in model save()
            'approval_date',           # Set by admin upon approval
            'status',                  # Defaults to 'pending', changed by admin
            'created_at',
        ]

    def validate_amount(self, value):
        """
        Ensure the requested loan amount is greater than zero.
        """
        if value <= 0:
            raise serializers.ValidationError("Loan amount must be greater than zero.")
        return value