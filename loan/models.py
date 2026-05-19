from django.db import models
from decimal import Decimal


class Loan(models.Model):
    SOCIAL = 'social'
    CONSTRUCTION = 'construction'
    COMMERCIAL = 'commercial'
    SALARY = 'salary'
    IBIMINA = 'ibimina'

    LOAN_TYPES = [
        (SOCIAL, 'Social Loan'),
        (CONSTRUCTION, 'Construction Loan'),
        (COMMERCIAL, 'Commercial Loan'),
        (SALARY, 'Salary Loan'),
        (IBIMINA, 'Ibimina Loan'),
    ]

    LAND = 'land'
    HOUSE = 'house'
    CAR = 'car'
    OTHER = 'other'

    COLLATERAL_TYPES = [
        (LAND, 'Land'),
        (HOUSE, 'House'),
        (CAR, 'Car'),
        (OTHER, 'Other'),
    ]

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    # Interest rate choices — bank allows 17%, 18%, or 19% annually
    INTEREST_RATE_CHOICES = [
        (Decimal('17.00'), '17% per year'),
        (Decimal('18.00'), '18% per year'),
        (Decimal('19.00'), '19% per year'),
    ]

    user_id = models.ForeignKey(
        'userapp.User',
        on_delete=models.CASCADE,
        related_name='loans',
        null=True, blank=True,
    )
    approved_by = models.ForeignKey(
        'userapp.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_loans',
    )

    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # User chooses between 17%, 18%, or 19%
    interest_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        choices=[(str(r), label) for r, label in INTEREST_RATE_CHOICES],
        default='17.00',
        help_text='Annual interest rate set by the bank (17% - 19%)',
    )

    # Automatically calculated fields — not editable by user
    annual_interest_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True, blank=True,
        editable=False,
        help_text='Interest amount per year (amount x interest_rate / 100)',
    )
    total_repayment_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True, blank=True,
        editable=False,
        help_text='Total amount to repay (principal + total interest)',
    )
    monthly_payment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True, blank=True,
        editable=False,
        help_text='Fixed monthly payment amount',
    )

    collateral_type = models.CharField(max_length=20, choices=COLLATERAL_TYPES)
    collateral_description = models.TextField(blank=True, null=True)
    application_date = models.DateTimeField(default=None, null=True, blank=True)
    approval_date = models.DateTimeField(blank=True, null=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def calculate_interest(self):
        """
        Calculate interest based on the selected annual rate.
        Formula:
            annual_interest  = amount x (interest_rate / 100)
            total_repayment  = amount + (annual_interest x duration_years)
            monthly_payment  = total_repayment / (duration_years x 12)
        Duration is fixed at 1 year. Bank controls the schedule.
        """
        if self.amount and self.interest_rate:
            rate = Decimal(str(self.interest_rate)) / Decimal('100')
            duration_years = Decimal('1')  # Bank sets 1 year duration

            self.annual_interest_amount = self.amount * rate
            self.total_repayment_amount = self.amount + (self.annual_interest_amount * duration_years)
            self.monthly_payment = self.total_repayment_amount / (duration_years * Decimal('12'))

    def save(self, *args, **kwargs):
        # Auto-calculate every time the loan is saved
        self.calculate_interest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.loan_type} - {self.amount} RWF @ {self.interest_rate}% ({self.status})"

# Create your models here.
