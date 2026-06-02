from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from loan.models import Loan

ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']
MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

LOAN_DURATION_CHOICES = [
    (12, '12 Months'),
]

REQUIRED_DOCS_BY_LOAN_TYPE = {
    'CONSTRUCTION': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'property_valuation', 'collateral_doc', 'building_permit',
    ],
    'COMMERCIAL': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'property_valuation', 'collateral_doc',
        'business_plan', 'trading_license',
    ],
    'SOCIAL': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'property_valuation', 'collateral_doc',
    ],
    'SALARY': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'collateral_doc', 'payslips', 'employment_letter',
    ],
    'IBIMINA': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'collateral_doc', 'ibimina_certificate',
    ],
}

PROVINCES = [
    ('Kigali', 'Kigali'),
    ('Northern', 'Northern'),
    ('Southern', 'Southern'),
    ('Eastern', 'Eastern'),
    ('Western', 'Western'),
]


def validate_document(file):
    ext = file.name.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(f'Invalid file type (.{ext}). Allowed: PDF, JPG, PNG.')
    if file.size == 0:
        raise ValidationError('The uploaded file is empty.')
    if file.size > MAX_SIZE_BYTES:
        raise ValidationError('File size exceeds the 5MB limit.')


def validate_pdf_only(file):
    ext = file.name.rsplit('.', 1)[-1].lower()
    if ext != 'pdf':
        raise ValidationError('Only PDF files are allowed for this document.')
    if file.size == 0:
        raise ValidationError('The uploaded file is empty.')
    if file.size > MAX_SIZE_BYTES:
        raise ValidationError('File size exceeds the 5MB limit.')


class LoanApplication(models.Model):
    user = models.ForeignKey(
        'userapp.User',
        on_delete=models.CASCADE,
        related_name='loan_applications',
    )

    # ── Personal Information ──
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    account_number = models.CharField(max_length=20)
    phone_number = models.CharField(
        max_length=13,
        validators=[RegexValidator(r'^\+?1?\d{10,13}$', 'Enter a valid phone number.')]
    )
    date_of_birth = models.DateField()

    # ── Street Address ──
    street_address = models.CharField(max_length=255)
    province = models.CharField(max_length=50, choices=PROVINCES)
    district = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=50, default='Rwanda')

    # ── Loan Specifics ──
    loan_type = models.CharField(max_length=20, choices=Loan.LOAN_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    loan_duration = models.PositiveIntegerField(
        choices=LOAN_DURATION_CHOICES,
        default=12,
        help_text='Loan duration in months — fixed at 12 months',
    )
    collateral_type = models.CharField(max_length=20, choices=Loan.COLLATERAL_TYPES)
    collateral_description = models.TextField(blank=True, null=True)

    # ── Submission Status ──
    DRAFT = 'DRAFT'
    SUBMITTED = 'SUBMITTED'
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (SUBMITTED, 'Submitted'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name} — {self.loan_type} — {self.amount}'


class LoanDocument(models.Model):
    application = models.OneToOneField(
        LoanApplication,
        on_delete=models.CASCADE,
        related_name='documents',
    )

    # ── Required for ALL loan types ──
    national_id = models.FileField(
        upload_to='documents/national_id/',
        validators=[validate_document],
        help_text='Personal national ID (front & back) — PDF, JPG or PNG, max 5MB',
    )
    guarantor_id = models.FileField(
        upload_to='documents/guarantor_id/',
        validators=[validate_document],
        help_text='Guarantor national ID — PDF, JPG or PNG, max 5MB',
    )
    civil_status_cert = models.FileField(
        upload_to='documents/civil_status_cert/',
        validators=[validate_document],
        help_text='Civil status certificate — PDF, JPG or PNG, max 5MB',
    )
    collateral_doc = models.FileField(
        upload_to='documents/collateral_doc/',
        validators=[validate_document],
        help_text='Collateral document / title — PDF, JPG or PNG, max 5MB',
    )

    # ── Construction & Commercial & Social ──
    property_valuation = models.FileField(
        upload_to='documents/property_valuation/',
        validators=[validate_document],
        null=True, blank=True,
        help_text='Property valuation document — PDF, JPG or PNG, max 5MB',
    )

    # ── Construction loan ──
    building_permit = models.FileField(
        upload_to='documents/building_permit/',
        validators=[validate_document],
        null=True, blank=True,
        help_text='Building permit — PDF, JPG or PNG, max 5MB',
    )

    # ── Commercial loan ──
    business_plan = models.FileField(
        upload_to='documents/business_plan/',
        validators=[validate_pdf_only],
        null=True, blank=True,
        help_text='Business plan — PDF only, max 5MB',
    )
    trading_license = models.FileField(
        upload_to='documents/trading_license/',
        validators=[validate_document],
        null=True, blank=True,
        help_text='Trading license — PDF, JPG or PNG, max 5MB',
    )

    # ── Salary loan ──
    payslips = models.FileField(
        upload_to='documents/payslips/',
        validators=[validate_document],
        null=True, blank=True,
        help_text='Last 3 months payslips — PDF, JPG or PNG, max 5MB',
    )
    employment_letter = models.FileField(
        upload_to='documents/employment_letter/',
        validators=[validate_document],
        null=True, blank=True,
        help_text='Employment confirmation letter — PDF, JPG or PNG, max 5MB',
    )

    # ── Ibimina loan ──
    ibimina_certificate = models.FileField(
        upload_to='documents/ibimina_certificate/',
        validators=[validate_document],
        null=True, blank=True,
        help_text='Ibimina group registration certificate — PDF, JPG or PNG, max 5MB',
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Documents for Application {self.application.id}'
