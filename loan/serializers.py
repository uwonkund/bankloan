from rest_framework import serializers
from loan.models import Loan


class LoanSerializer(serializers.ModelSerializer):
    loan_type_display = serializers.CharField(source='get_loan_type_display', read_only=True)
    collateral_type_display = serializers.CharField(source='get_collateral_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    loan_token = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_token', 'loan_type', 'loan_type_display',
            'amount', 'interest_rate',
            'annual_interest_amount', 'total_repayment_amount', 'monthly_payment',
            'collateral_type', 'collateral_type_display', 'collateral_description',
            'application_date', 'approval_date',
            'status', 'status_display', 'created_at',
        ]
        read_only_fields = [
            'id', 'loan_token', 'annual_interest_amount',
            'total_repayment_amount', 'monthly_payment',
            'status', 'approval_date', 'created_at',
        ]

    def get_loan_token(self, obj):
        return f'LN-{obj.id:06d}'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Loan amount must be greater than zero.')
        return value


class LoanAdminSerializer(LoanSerializer):
    class Meta(LoanSerializer.Meta):
        read_only_fields = ['id', 'loan_token', 'annual_interest_amount',
                            'total_repayment_amount', 'monthly_payment', 'created_at']
