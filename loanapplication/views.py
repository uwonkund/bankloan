from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view
from loanapplication.models import LoanApplication, LoanDocument, REQUIRED_DOCS_BY_LOAN_TYPE
from loanapplication.serializers import LoanApplicationSerializer, LoanDocumentSerializer, SubmissionConfirmationSerializer


@extend_schema_view(
    list=extend_schema(summary='List my loan applications'),
    retrieve=extend_schema(summary='Retrieve a loan application'),
    create=extend_schema(
        summary='Create a Loan Application (Draft)',
        description=(
            'Create a loan application as a draft. Fill in all fields then '
            'upload documents, and finally call POST /api/loanapplication/applications/{id}/submit/ '
            'to submit it to the bank.\n\n'
            '**Personal Information:** first_name, last_name, email, account_number, '
            'phone_number, date_of_birth (YYYY-MM-DD)\n\n'
            '**Street Address:** street_address, province (Kigali / Northern / Southern / '
            'Eastern / Western), district, postal_code, country (default: Rwanda)\n\n'
            '**Loan Specifics:** loan_type, amount, interest_rate, '
            'loan_duration (fixed: 12), collateral_type, collateral_description'
        ),
    ),
    update=extend_schema(summary='Update a loan application'),
    partial_update=extend_schema(summary='Partially update a loan application'),
    destroy=extend_schema(summary='Delete a loan application'),
)
class LoanApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LoanApplication.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary='Submit Application',
        description=(
            'Finalizes and submits the loan application to the bank for review.\n\n'
            'Before submitting, the application must have:\n'
            '- All personal information and loan details filled in\n'
            '- All required documents uploaded based on the loan type\n\n'
            'Once submitted, the status changes from **DRAFT** to **SUBMITTED** '
            'and the application cannot be edited.'
        ),
        request=None,
        responses={
            200: LoanApplicationSerializer,
            400: None,
        },
    )
    @action(detail=True, methods=['post'], url_path='submit')
    def submit(self, request, pk=None):
        application = self.get_object()

        # Prevent re-submission
        if application.status == LoanApplication.SUBMITTED:
            return Response(
                {'detail': 'This application has already been submitted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check documents are uploaded
        if not hasattr(application, 'documents'):
            return Response(
                {'detail': 'Please upload the required documents before submitting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check all required docs for the loan type are present
        loan_type = application.loan_type.strip().upper()
        required_docs = REQUIRED_DOCS_BY_LOAN_TYPE.get(loan_type, [])
        docs = application.documents
        missing = [
            field for field in required_docs
            if not getattr(docs, field, None)
        ]
        if missing:
            return Response(
                {
                    'detail': 'Missing required documents.',
                    'missing_documents': missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark as submitted
        application.status = LoanApplication.SUBMITTED
        application.submitted_at = timezone.now()
        application.save(update_fields=['status', 'submitted_at'])

        serializer = SubmissionConfirmationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary='List loan documents'),
    retrieve=extend_schema(summary='Retrieve loan documents'),
    create=extend_schema(
        summary='Upload Documents',
        description=(
            'Upload required documents for a loan application (multipart/form-data).\n\n'
            '**Required for ALL loan types:** national_id, guarantor_id, '
            'civil_status_cert, collateral_doc\n\n'
            '**CONSTRUCTION:** + property_valuation, building_permit\n\n'
            '**COMMERCIAL:** + property_valuation, business_plan (PDF only), trading_license\n\n'
            '**SOCIAL:** + property_valuation\n\n'
            '**SALARY:** + payslips, employment_letter\n\n'
            '**IBIMINA:** + ibimina_certificate\n\n'
            'Allowed formats: PDF, JPG, PNG — max 5MB each.'
        ),
    ),
    update=extend_schema(summary='Replace uploaded documents'),
    partial_update=extend_schema(summary='Update specific documents'),
    destroy=extend_schema(summary='Delete loan documents'),
)
class LoanDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = LoanDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LoanDocument.objects.filter(application__user=self.request.user)
