from django import forms
from .models import User
from loan.models import Loan


# ──────────────────────────────────────────────
# Required docs per loan type
# ──────────────────────────────────────────────

REQUIRED_DOCS_BY_LOAN_TYPE = {
    'construction': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'property_valuation', 'collateral_doc', 'building_permit',
    ],
    'commercial': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'property_valuation', 'collateral_doc',
        'business_plan', 'trading_license',
    ],
    'social': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'property_valuation', 'collateral_doc',
    ],
    'salary': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'collateral_doc', 'payslips', 'employment_letter',
    ],
    'ibimina': [
        'national_id', 'guarantor_id', 'civil_status_cert',
        'collateral_doc', 'ibimina_certificate',
    ],
}


# ──────────────────────────────────────────────
# Document upload form
# ──────────────────────────────────────────────

class LoanDocumentForm(forms.Form):

    # ── Standard documents — required for ALL loan types ──
    national_id = forms.FileField(
        label='Personal national ID (front & back)',
        help_text='PDF, JPG or PNG — max 5MB',
    )
    guarantor_id = forms.FileField(
        label='Guarantor national ID',
        help_text='PDF, JPG or PNG — max 5MB',
    )
    civil_status_cert = forms.FileField(
        label='Civil status certificate',
        help_text='PDF, JPG or PNG — max 5MB',
    )
    property_valuation = forms.FileField(
        label='Property valuation document',
        help_text='PDF, JPG or PNG — max 5MB',
    )
    collateral_doc = forms.FileField(
        label='Collateral document / title',
        help_text='PDF, JPG or PNG — max 5MB',
    )

    # ── Construction loan ──
    building_permit = forms.FileField(
        required=False,
        label='Building permit',
        help_text='PDF, JPG or PNG — max 5MB',
    )

    # ── Commercial loan ──
    business_plan = forms.FileField(
        required=False,
        label='Business plan',
        help_text='PDF only — max 5MB',
    )
    trading_license = forms.FileField(
        required=False,
        label='Trading license',
        help_text='PDF, JPG or PNG — max 5MB',
    )

    # ── Salary loan ──
    payslips = forms.FileField(
        required=False,
        label='Last 3 months payslips',
        help_text='PDF, JPG or PNG — max 5MB',
    )
    employment_letter = forms.FileField(
        required=False,
        label='Employment confirmation letter',
        help_text='PDF, JPG or PNG — max 5MB',
    )

    # ── Ibimina loan ──
    ibimina_certificate = forms.FileField(
        required=False,
        label='Ibimina group registration certificate',
        help_text='PDF, JPG or PNG — max 5MB',
    )

    def __init__(self, *args, loan_type=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Mark loan-type-specific docs as required
        required_docs = REQUIRED_DOCS_BY_LOAN_TYPE.get(loan_type, [])
        for field_name in required_docs:
            if field_name in self.fields:
                self.fields[field_name].required = True

        # Restrict every field to file picker only — no text input
        for field_name, field in self.fields.items():
            field.widget = forms.ClearableFileInput(attrs={
                'accept': self._allowed_types(field_name),
                'class': 'doc-upload-input',
            })

    def _allowed_types(self, field_name):
        """Return accepted MIME types per field."""
        if field_name == 'business_plan':
            return 'application/pdf'
        return 'application/pdf,image/jpeg,image/png'

    def clean(self):
        cleaned_data = super().clean()

        ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']
        MAX_SIZE_BYTES = 5 * 1024 * 1024  # 5MB

        for field_name, file in cleaned_data.items():
            if file is None:
                continue

            # Must be a real uploaded file object, not typed text
            if not hasattr(file, 'name'):
                self.add_error(
                    field_name,
                    'Please upload a file. Do not type in this field.',
                )
                continue

            # Validate extension
            ext = file.name.rsplit('.', 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                self.add_error(
                    field_name,
                    f'Invalid file type (.{ext}). Allowed formats: PDF, JPG, PNG.',
                )

            # Validate size
            if file.size > MAX_SIZE_BYTES:
                self.add_error(
                    field_name,
                    f'File size ({file.size // (1024 * 1024)}MB) exceeds the 5MB limit.',
                )

            # Validate file is not empty
            if file.size == 0:
                self.add_error(
                    field_name,
                    'The uploaded file appears to be empty. Please upload a valid document.',
                )

        return cleaned_data


# ──────────────────────────────────────────────
# Main application form
# ──────────────────────────────────────────────

class LoanApplicationForm(forms.Form):
    # User fields
    account_number = forms.CharField(max_length=20)
    name           = forms.CharField(max_length=100)
    email          = forms.EmailField()
    phone          = forms.CharField(max_length=20)
    address        = forms.CharField(widget=forms.Textarea)

    # Loan fields
    loan_type     = forms.ChoiceField(choices=Loan.LOAN_TYPES)
    amount        = forms.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = forms.DecimalField(max_digits=5,  decimal_places=2)

    # Collateral
    collateral_type        = forms.ChoiceField(choices=Loan.COLLATERAL_TYPES)
    collateral_description = forms.CharField(
        widget=forms.Textarea,
        required=False,
    )