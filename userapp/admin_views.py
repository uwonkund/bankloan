from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime
from userapp.models import User
from loanapplication.models import LoanApplication
from loan.models import Loan
from payment.models import Payment


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary='Admin Dashboard',
        tags=['Admin'],
        description='Bank admin dashboard with system statistics. Only accessible to admin users.',
        responses={
            200: OpenApiResponse(description='Admin dashboard data'),
            403: OpenApiResponse(description='Access denied - admin only'),
        },
    )
    def get(self, request):
        # Check if user is admin
        if request.user.user_type != User.ADMIN:
            return Response(
                {'detail': 'Access denied. Admin privileges required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get system statistics
        # Total Borrowers - count of users with USER type (customers)
        total_borrowers = User.objects.filter(user_type=User.USER).count()
        
        # Loan Portfolio - sum of all disbursed loans (approved loans amount)
        loan_portfolio = Loan.objects.filter(status='APPROVED').aggregate(
            total_amount=Sum('amount')
        )['total_amount'] or 0
        
        # Total Repaid - sum of all payments made by customers
        total_repaid = Payment.objects.aggregate(
            total_amount=Sum('amount_paid')
        )['total_amount'] or 0
        
        # Additional stats
        total_loan_applications = LoanApplication.objects.count()
        total_active_loans = Loan.objects.filter(status='APPROVED').count()
        total_payments = Payment.objects.count()
        
        # Calculate repayment rate if there are loans
        repayment_rate = 0
        if loan_portfolio > 0:
            repayment_rate = (total_repaid / loan_portfolio) * 100
        
        # Get today's date for filtering
        today = timezone.now().date()
        
        # Repayment Status - Today's payments
        today_payments = Payment.objects.filter(
            payment_date__date=today
        ).aggregate(
            total_amount=Sum('amount_paid')
        )['total_amount'] or 0
        
        # Pending Review - Loan applications with SUBMITTED status (awaiting review)
        pending_reviews = LoanApplication.objects.filter(status='SUBMITTED').count()
        
        # All Customer Applicants - List of all users with USER type
        all_customers = User.objects.filter(user_type=User.USER).order_by('-created_on')
        customers_data = [
            {
                'id': customer.id,
                'email': customer.email,
                'full_name': customer.full_name,
                'phone_number': customer.phone_number,
                'account_number': customer.account_number,
                'created_on': customer.created_on,
                'is_active': customer.is_active,
            }
            for customer in all_customers
        ]
        
        # Get recent loan applications (last 10)
        recent_applications = LoanApplication.objects.select_related('user').order_by('-created_at')[:10]
        recent_apps_data = [
            {
                'id': app.id,
                'user_email': app.user.email,
                'user_name': app.user.full_name,
                'loan_type': app.loan_type,
                'amount': app.amount,
                'status': app.status,
                'created_at': app.created_at,
            }
            for app in recent_applications
        ]
        
        # Get recent payments (last 10)
        recent_payments = Payment.objects.select_related('loan', 'loan__user_id').order_by('-payment_date')[:10]
        recent_payments_data = [
            {
                'id': payment.id,
                'user_email': payment.loan.user_id.email if payment.loan and payment.loan.user_id else 'N/A',
                'user_name': payment.loan.user_id.full_name if payment.loan and payment.loan.user_id else 'N/A',
                'amount': float(payment.amount_paid),
                'payment_date': payment.payment_date,
                'payment_method': payment.payment_method,
            }
            for payment in recent_payments
        ]
        
        # Get pending loan applications for review
        pending_applications = LoanApplication.objects.filter(
            status='SUBMITTED'
        ).select_related('user').order_by('-created_at')
        pending_apps_data = [
            {
                'id': app.id,
                'user_email': app.user.email if app.user else 'N/A',
                'user_name': app.user.full_name if app.user else 'N/A',
                'loan_type': app.loan_type,
                'amount': app.amount,
                'created_at': app.created_at,
            }
            for app in pending_applications
        ]
        
        return Response({
            'dashboard_stats': {
                'total_borrowers': total_borrowers,
                'loan_portfolio': float(loan_portfolio),
                'total_repaid': float(total_repaid),
                'repayment_rate': round(repayment_rate, 2),
                'total_loan_applications': total_loan_applications,
                'total_active_loans': total_active_loans,
                'total_payments': total_payments,
            },
            'repayment_status': {
                'total_paid_today': float(today_payments),
                'pending_reviews': pending_reviews,
            },
            'all_customers': customers_data,
            'recent_loan_applications': recent_apps_data,
            'recent_payments': recent_payments_data,
            'pending_applications': pending_apps_data,
            'admin_info': {
                'email': request.user.email,
                'full_name': request.user.full_name,
                'user_type': request.user.user_type,
            }
        }, status=status.HTTP_200_OK)