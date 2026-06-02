from decimal import Decimal
from django.db.models import Sum
from rest_framework import serializers
from payment.models import PaymentSchedule, Payment, Penalty
from loan.models import Loan

# Processing fees per payment method
PROCESSING_FEES = {
    'linked_bank_account': Decimal('0.00'),   # No fee
    'debit_credit_card':   Decimal('1.50'),   # 1.5% of amount
    'mobile_money':        Decimal('1.00'),   # 1.0% of amount
}

PAYMENT_METHOD_CHOICES = [
    ('linked_bank_account', 'Linked Bank Account'),
    ('debit_credit_card',   'Debit / Credit Card'),
    ('mobile_money',        'Mobile Money'),
]


class PaymentScheduleSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = PaymentSchedule
        fields = [
            'id', 'month_number', 'due_date',
            'amount_due', 'interest_due', 'total_due',
            'amount_paid', 'balance',
            'status', 'status_display', 'is_paid', 'paid_at',
        ]
        read_only_fields = fields


class PenaltySerializer(serializers.ModelSerializer):
    class Meta:
        model = Penalty
        fields = [
            'id', 'penalty_type', 'penalty_rate',
            'original_amount', 'penalty_amount', 'total_amount_due',
            'months_missed', 'status', 'applied_at', 'note',
        ]
        read_only_fields = fields


class MyLoanSerializer(serializers.ModelSerializer):
    """Used for My Loan page — tracking, history, and new loan button."""
    loan_token = serializers.SerializerMethodField()
    loan_type_display = serializers.CharField(source='get_loan_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_schedules = PaymentScheduleSerializer(many=True, read_only=True)
    penalties = PenaltySerializer(many=True, read_only=True)
    paid_months = serializers.SerializerMethodField()
    remaining_months = serializers.SerializerMethodField()
    current_balance = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_token', 'loan_type', 'loan_type_display',
            'amount', 'interest_rate', 'monthly_payment',
            'total_repayment_amount', 'current_balance',
            'status', 'status_display',
            'application_date', 'approval_date', 'created_at',
            'paid_months', 'remaining_months',
            'payment_schedules', 'penalties',
        ]
        read_only_fields = fields

    def get_loan_token(self, obj):
        return f'LN-{obj.id:06d}'

    def get_paid_months(self, obj):
        return obj.payment_schedules.filter(is_paid=True).count()

    def get_remaining_months(self, obj):
        return obj.payment_schedules.filter(is_paid=False).count()

    def get_current_balance(self, obj):
        return obj.payment_schedules.filter(
            is_paid=False
        ).aggregate(total=Sum('total_due'))['total'] or 0


class DashboardPaymentHistorySerializer(serializers.ModelSerializer):
    """Compact payment history for the dashboard."""
    loan_token = serializers.SerializerMethodField()
    month_number = serializers.IntegerField(source='schedule.month_number', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'loan_token', 'month_number',
            'amount_paid', 'payment_method', 'payment_method_display',
            'status', 'payment_date',
        ]
        read_only_fields = fields

    def get_loan_token(self, obj):
        return f'LN-{obj.loan.id:06d}'


class PaymentSummarySerializer(serializers.Serializer):
    """
    Preview shown after selecting payment method — before confirming Pay Now.
    Send: loan, schedule, amount_paid, payment_method.
    Returns: payment_amount, processing_fee, total_amount, payment_method_display.
    """
    loan = serializers.PrimaryKeyRelatedField(queryset=Loan.objects.all())
    schedule = serializers.PrimaryKeyRelatedField(queryset=PaymentSchedule.objects.all())
    amount_paid = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_method = serializers.ChoiceField(choices=PAYMENT_METHOD_CHOICES)

    # Read-only computed fields returned in response
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    processing_fee = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    processing_fee_note = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    payment_method_display = serializers.CharField(read_only=True)

    def validate(self, attrs):
        schedule = attrs.get('schedule')
        loan = attrs.get('loan')
        if schedule.loan != loan:
            raise serializers.ValidationError(
                {'schedule': 'This schedule does not belong to the selected loan.'}
            )
        if schedule.is_paid:
            raise serializers.ValidationError(
                {'schedule': 'This month has already been fully paid.'}
            )
        if attrs['amount_paid'] <= 0:
            raise serializers.ValidationError(
                {'amount_paid': 'Payment amount must be greater than zero.'}
            )
        return attrs

    def to_representation(self, instance):
        """Compute and return the payment summary."""
        amount = Decimal(str(instance['amount_paid']))
        method = instance['payment_method']
        fee_rate = PROCESSING_FEES.get(method, Decimal('0.00'))
        processing_fee = (amount * fee_rate / Decimal('100')).quantize(Decimal('0.01'))
        total = (amount + processing_fee).quantize(Decimal('0.01'))

        method_display = dict(PAYMENT_METHOD_CHOICES).get(method, method)

        fee_note = {
            'linked_bank_account': 'No processing fee for linked bank account.',
            'debit_credit_card':   '1.5% processing fee applies for debit/credit card.',
            'mobile_money':        '1.0% processing fee applies for mobile money.',
        }.get(method, '')

        return {
            'loan': instance['loan'].id,
            'schedule': instance['schedule'].id,
            'payment_amount': str(amount),
            'payment_method': method,
            'payment_method_display': method_display,
            'processing_fee': str(processing_fee),
            'processing_fee_note': fee_note,
            'total_amount': str(total),
        }


class MakePaymentSerializer(serializers.ModelSerializer):
    """Used for the Payments page — submits the payment after confirming Pay Now."""
    payment_method = serializers.ChoiceField(choices=PAYMENT_METHOD_CHOICES)

    class Meta:
        model = Payment
        fields = ['id', 'loan', 'schedule', 'amount_paid', 'payment_method', 'note', 'status', 'payment_date']
        read_only_fields = ['id', 'status', 'payment_date']

    def validate_amount_paid(self, value):
        if value <= 0:
            raise serializers.ValidationError('Payment amount must be greater than zero.')
        return value

    def validate(self, attrs):
        schedule = attrs.get('schedule')
        loan = attrs.get('loan')
        if schedule and schedule.loan != loan:
            raise serializers.ValidationError(
                {'schedule': 'This schedule does not belong to the selected loan.'}
            )
        if schedule and schedule.is_paid:
            raise serializers.ValidationError(
                {'schedule': 'This month has already been fully paid.'}
            )
        return attrs


class PaymentReceiptSerializer(serializers.ModelSerializer):
    """Returned after a successful Pay Now — full payment receipt."""
    loan_token = serializers.SerializerMethodField()
    month_number = serializers.IntegerField(source='schedule.month_number', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    processing_fee = serializers.SerializerMethodField()
    processing_fee_note = serializers.SerializerMethodField()
    total_amount_paid = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'loan_token', 'loan', 'schedule', 'month_number',
            'amount_paid', 'processing_fee', 'processing_fee_note',
            'total_amount_paid', 'payment_method', 'payment_method_display',
            'status', 'payment_date',
        ]
        read_only_fields = fields

    def get_loan_token(self, obj):
        return f'LN-{obj.loan.id:06d}'

    def get_processing_fee(self, obj):
        fee_rate = PROCESSING_FEES.get(obj.payment_method, Decimal('0.00'))
        return str((Decimal(str(obj.amount_paid)) * fee_rate / Decimal('100')).quantize(Decimal('0.01')))

    def get_processing_fee_note(self, obj):
        return {
            'linked_bank_account': 'No processing fee for linked bank account.',
            'debit_credit_card':   '1.5% processing fee applies for debit/credit card.',
            'mobile_money':        '1.0% processing fee applies for mobile money.',
        }.get(obj.payment_method, '')

    def get_total_amount_paid(self, obj):
        fee_rate = PROCESSING_FEES.get(obj.payment_method, Decimal('0.00'))
        fee = Decimal(str(obj.amount_paid)) * fee_rate / Decimal('100')
        return str((Decimal(str(obj.amount_paid)) + fee).quantize(Decimal('0.01')))


class CurrentBalanceSerializer(serializers.ModelSerializer):
    """Used for the Payments page header — shows balance and next due date."""
    loan_token = serializers.SerializerMethodField()
    current_balance = serializers.SerializerMethodField()
    next_due_date = serializers.SerializerMethodField()
    next_due_amount = serializers.SerializerMethodField()
    next_schedule_id = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id', 'loan_token', 'loan_type', 'amount',
            'monthly_payment', 'current_balance',
            'next_due_date', 'next_due_amount', 'next_schedule_id',
            'status',
        ]
        read_only_fields = fields

    def get_loan_token(self, obj):
        return f'LN-{obj.id:06d}'

    def get_current_balance(self, obj):
        return obj.payment_schedules.filter(
            is_paid=False
        ).aggregate(total=Sum('total_due'))['total'] or 0

    def _get_next_schedule(self, obj):
        if not hasattr(obj, '_next_schedule_cache'):
            obj._next_schedule_cache = obj.payment_schedules.filter(
                is_paid=False
            ).order_by('due_date').first()
        return obj._next_schedule_cache

    def get_next_due_date(self, obj):
        s = self._get_next_schedule(obj)
        return s.due_date if s else None

    def get_next_due_amount(self, obj):
        s = self._get_next_schedule(obj)
        return s.total_due if s else None

    def get_next_schedule_id(self, obj):
        s = self._get_next_schedule(obj)
        return s.id if s else None
