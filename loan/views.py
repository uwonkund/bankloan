from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, extend_schema_view
from loan.models import Loan
from loan.serializers import LoanSerializer, LoanAdminSerializer


# @extend_schema_view(
#     list=extend_schema(
#         summary='My Loans',
#         description='List all loans for the logged-in user. Admins see all loans.',
#     ),
#     retrieve=extend_schema(
#         summary='Loan Detail',
#         description='Get full details of a single loan including token, monthly payment and status.',
#     ),
#     create=extend_schema(
#         summary='Apply for a Loan',
#         description='Submit a new loan application. Status starts as PENDING until approved by admin.',
#     ),
#     update=extend_schema(summary='Update Loan'),
#     partial_update=extend_schema(summary='Partially Update Loan'),
#     destroy=extend_schema(summary='Delete Loan'),
# )
@extend_schema(tags=['Loans'])
class LoanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.user.is_staff:
            return LoanAdminSerializer
        return LoanSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Loan.objects.all().order_by('-created_at')
        return Loan.objects.filter(user_id=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.user)

    def perform_update(self, serializer):
        if self.request.user.is_staff:
            serializer.save(approved_by=self.request.user)
        else:
            serializer.save()
