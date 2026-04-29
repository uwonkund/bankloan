from django.db import models


class Loan(models.Model):
    PERSONAL = 'personal'
    BUSINESS = 'business'
    EDUCATION = 'education'

    LOAN_TYPES = [
        (PERSONAL, 'Personal Loan'),
        (BUSINESS, 'Business Loan'),
        (EDUCATION, 'Education Loan'),
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

    # 🔹 Approval status choices
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECTED, 'Rejected'),
    ]

    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)

    collateral_type = models.CharField(max_length=20, choices=COLLATERAL_TYPES)
    collateral_description = models.TextField(blank=True, null=True)

    # 🔹 Approval field
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.loan_type} - {self.amount} ({self.status})"

# Create your models here.
