from django.urls import path
from payment.views import MyLoanView, CurrentBalanceView, PaymentSummaryView, MakePaymentView, PaymentHistoryView

urlpatterns = [
    path('my-loans/', MyLoanView.as_view(), name='my_loans'),
    path('balance/', CurrentBalanceView.as_view(), name='current_balance'),
    path('summary/', PaymentSummaryView.as_view(), name='payment_summary'),
    path('pay/', MakePaymentView.as_view(), name='make_payment'),
    path('history/', PaymentHistoryView.as_view(), name='payment_history'),
]
