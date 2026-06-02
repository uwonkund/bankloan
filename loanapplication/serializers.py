from decimal import Decimal
from datetime import date
from dateutil.relativedelta import relativedelta
from rest_framework import serializers
from loanapplication.models import (
    LoanApplication, LoanDocument,
    REQUIRED_DOCS_BY_LOAN_TYPE, ALLOWED_EXTENSIONS, MAX_SIZE_BYTES,
)


class LoanDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = LoanDocument
        fields = [
            'id', 'application',
            'national_id', 'guarantor_id', 'civil_status_cert',
            'collateral_doc', 'property_valuation', 'building_permit',
            'business_plan', 'trading_license',
            'payslips', 'employment_letter', 'ibimina_certificate',
            'uploaded_at',
        ]
        read_only_fields = ['id', 'uploaded_at']

    def _validate_file(self, file, pdf_only=False):
        if not hasattr(file, 'name'):
            raise serializers.ValidationError('Please upload a file, do not type in this field.')
        ext = file.name.rsplit('.', 1)[-1].lower()
        allowed = ['pdf'] if pdf_only else ALLOWED_EXTENSIONS
        if ext not in allowed:
            raise serializers.ValidationError(
                f'Invalid file type (.{ext}). Allowed: {", ".join(allowed).upper()}.'
            )
        if file.size == 0:
            raise serializers.ValidationError('The uploaded file is empty.')
        if file.size > MAX_SIZE_BYTES:
            raise serializers.ValidationError('File size exceeds the 5MB limit.')
        return file

    def validate_business_plan(self, value):
        if value:
            return self._validate_file(value, pdf_only=True)
        return value

    def validate(self, attrs):
        application = attrs.get('application') or (
            self.instance.application if self.instance else None
        )

        if application:
            loan_type = application.loan_type.strip().upper()
            required_docs = REQUIRED_DOCS_BY_LOAN_TYPE.get(loan_type, [])
            errors = {}
            for field in required_docs:
                value = attrs.get(field) or (
                    getattr(self.instance, field, None) if self.instance else None
                )
                if not value:
                    errors[field] = f'This document is required for {loan_type} loans.'
            if errors:
                raise serializers.ValidationError(errors)

        doc_fields = [
            'national_id', 'guarantor_id', 'civil_status_cert', 'collateral_doc',
            'property_valuation', 'building_permit', 'trading_license',
            'payslips', 'employment_letter', 'ibimina_certificate',
        ]
        errors = {}
        for field in doc_fields:
            file = attrs.get(field)
            if file:
                try:
                    self._validate_file(file)
                except serializers.ValidationError as e:
                    errors[field] = e.detail
        if errors:
            raise serializers.ValidationError(errors)

        return attrs


class LoanApplicationSerializer(serializers.ModelSerializer):
    documents = LoanDocumentSerializer(read_only=True)
    loan_duration_display = serializers.SerializerMethodField()

    class Meta:
        model = LoanApplication
        fields = [
            'id', 'user',
            'first_name', 'last_name', 'email', 'account_number',
            'phone_number', 'date_of_birth',
            'street_address', 'province', 'district', 'postal_code', 'country',
            'loan_type', 'amount', 'interest_rate',
            'loan_duration', 'loan_duration_display',
            'collateral_type', 'collateral_description',
            'status', 'submitted_at',
            'created_at', 'documents',
        ]
        read_only_fields = ['id', 'user', 'loan_duration_display', 'status', 'submitted_at', 'created_at']

    def get_loan_duration_display(self, obj):
        return f'{obj.loan_duration} Months'

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Loan amount must be greater than zero.')
        return value

    def validate_date_of_birth(self, value):
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18:
            raise serializers.ValidationError('Applicant must be at least 18 years old.')
        return value


class SubmissionConfirmationSerializer(serializers.ModelSerializer):
    """Returned after a successful submit — shows the loan summary confirmation screen."""
    loan_type_display = serializers.CharField(source='get_loan_type_display', read_only=True)
    loan_duration_display = serializers.SerializerMethodField()
    requested_amount = serializers.DecimalField(source='amount', max_digits=10, decimal_places=2, read_only=True)
    total_loan_amount = serializers.SerializerMethodField()
    monthly_payment = serializers.SerializerMethodField()
    due_date = serializers.SerializerMethodField()

    class Meta:
        model = LoanApplication
        fields = [
            'id',
            'loan_type',
            'loan_type_display',
            'loan_duration',
            'loan_duration_display',
            'requested_amount',
            'interest_rate',
            'total_loan_amount',
            'monthly_payment',
            'due_date',
            'status',
            'submitted_at',
        ]
        read_only_fields = fields

    def get_loan_duration_display(self, obj):
        return f'{obj.loan_duration} Months'

    def get_total_loan_amount(self, obj):
        """requested_amount + (requested_amount x interest_rate / 100)"""
        amount = Decimal(str(obj.amount))
        rate = Decimal(str(obj.interest_rate)) / Decimal('100')
        return (amount + (amount * rate)).quantize(Decimal('0.01'))

    def get_monthly_payment(self, obj):
        """total_loan_amount / loan_duration"""
        amount = Decimal(str(obj.amount))
        rate = Decimal(str(obj.interest_rate)) / Decimal('100')
        total = amount + (amount * rate)
        return (total / Decimal(str(obj.loan_duration))).quantize(Decimal('0.01'))

    def get_due_date(self, obj):
        """submitted_at + loan_duration months = final repayment due date"""
        if not obj.submitted_at:
            return None
        return (obj.submitted_at + relativedelta(months=obj.loan_duration)).date()
