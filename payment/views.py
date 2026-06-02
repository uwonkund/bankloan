from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from loan.models import Loan
from payment.models import Payment
from payment.serializers import (
    MyLoanSerializer,
    CurrentBalanceSerializer,
    MakePaymentSerializer,
    PaymentSummarySerializer,
    PaymentReceiptSerializer,
)


class MyLoanView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='My Loans',
        description=(
            'Returns all loans for the logged-in user with full payment tracking, '
            'schedule history per month, penalties, paid/remaining months, and current balance.'
        ),
        responses={200: MyLoanSerializer(many=True)},
    )
    def get(self, request):
        loans = Loan.objects.filter(user_id=request.user).order_by('-created_at')
        serializer = MyLoanSerializer(loans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CurrentBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Current Balance & Next Due Date',
        description=(
            'Returns the active approved loan balance, next due date, next due amount, '
            'and the schedule ID to use when making a payment.'
        ),
        responses={200: CurrentBalanceSerializer},
    )
    def get(self, request):
        loan = Loan.objects.filter(
            user_id=request.user, status='APPROVED'
        ).order_by('-created_at').first()

        if not loan:
            return Response(
                {'detail': 'No active approved loan found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CurrentBalanceSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PaymentSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Payment Summary Preview',
        description=(
            'Returns a payment summary preview after the client selects a payment method. '
            'Shows payment amount, processing fee, and total amount before confirming Pay Now.\n\n'
            'Processing fees:\n'
            '- `linked_bank_account` — No fee\n'
            '- `debit_credit_card` — 1.5% of payment amount\n'
            '- `mobile_money` — 1.0% of payment amount\n\n'
            'Send: loan, schedule, amount_paid, payment_method.\n'
            'Then confirm by calling POST /api/payment/pay/'
        ),
        request=PaymentSummarySerializer,
        responses={
            200: PaymentSummarySerializer,
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request):
        serializer = PaymentSummarySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.to_representation(serializer.validated_data), status=status.HTTP_200_OK)


class MakePaymentView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MakePaymentSerializer

    @extend_schema(
        summary='Pay Now',
        description=(
            'Confirm and submit the payment after reviewing the payment summary.\n\n'
            'Provide: loan, schedule, amount_paid, payment_method.\n\n'
            'Returns a full payment receipt including processing fee and total amount paid.\n\n'
            'After payment the schedule balance is updated automatically. '
            'If a penalty exists for that month it is resolved automatically.'
        ),
        responses={
            201: PaymentReceiptSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(status='success')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        receipt = PaymentReceiptSerializer(serializer.instance)
        return Response(receipt.data, status=status.HTTP_201_CREATED)


class PaymentHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Payment History',
        description='Returns all payments made by the logged-in user across all loans.',
        responses={200: PaymentReceiptSerializer(many=True)},
    )
    def get(self, request):
        payments = Payment.objects.filter(
            loan__user_id=request.user
        ).order_by('-payment_date')
        serializer = PaymentReceiptSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
