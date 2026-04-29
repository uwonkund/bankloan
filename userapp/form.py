from django import forms
from .models import Customer
from loan.models import Loan


class LoanApplicationForm(forms.Form):
    # Customer fields
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    address = forms.CharField(widget=forms.Textarea)

    # Loan fields
    loan_type = forms.ChoiceField(choices=Loan.LOAN_TYPES)
    amount = forms.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = forms.DecimalField(max_digits=5, decimal_places=2)

    # Collateral
    collateral_type = forms.ChoiceField(choices=Loan.COLLATERAL_TYPES)
    collateral_description = forms.CharField(
        widget=forms.Textarea,
        required=False
    )