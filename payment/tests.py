from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Loan
from .serializers import LoanSerializer

User = get_user_model()


class LoanModelTestCase(TestCase):
    """Test suite for the Loan model logic and calculations."""

    def setUp(self):
        # Create a test user for foreign keys
        self.user = User.objects.create_user(
            username="borrower", 
            email="borrower@example.com", 
            password="securepassword123"
        )

    def test_loan_interest_calculation_on_save(self):
        """
        Verify that interest, total repayment, and monthly payments 
        are auto-calculated properly when a loan is saved.
        Formula check for 100,000 RWF at 18% interest for 1 year:
        - annual_interest = 100,000 * 0.18 = 18,000
        - total_repayment = 100,000 + 18,000 = 118,000
        - monthly_payment = 118,000 / 12 = 9,833.33
        """
        loan = Loan.objects.create(
            user_id=self.user,
            loan_type=Loan.SOCIAL,
            amount=Decimal("100000.00"),
            interest_rate=Decimal("18.00"),
            collateral_type=Loan.LAND,
            collateral_description="Plot 402 Kigali"
        )

        # Assertions
        self.assertEqual(loan.annual_interest_amount, Decimal("18000.00"))
        self.assertEqual(loan.total_repayment_amount, Decimal("118000.00"))
        # Using round to mitigate minor floating point/decimal precision differences
        self.assertAlmostEqual(loan.monthly_payment, Decimal("118000.00") / 12, places=2)
        self.assertEqual(loan.status, Loan.PENDING)

    def test_str_representation(self):
        """Test the __str__ output format."""
        loan = Loan.objects.create(
            user_id=self.user,
            loan_type=Loan.IBIMINA,
            amount=Decimal("50000.00"),
            interest_rate=Decimal("17.00"),
            collateral_type=Loan.OTHER
        )
        expected_str = f"ibimina - 50000.00 RWF @ 17.00% (pending)"
        self.assertEqual(str(loan), expected_str)


class LoanSerializerTestCase(TestCase):
    """Test suite for LoanSerializer validation and data structures."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="client", 
            email="client@example.com", 
            password="password123"
        )

    def test_serializer_validation_invalid_amount(self):
        """Serializer should reject amounts less than or equal to zero."""
        invalid_data = {
            "user_id": self.user.id,
            "loan_type": Loan.SALARY,
            "amount": "0.00",
            "interest_rate": "17.00",
            "collateral_type": Loan.CAR
        }
        serializer = LoanSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("amount", serializer.errors)

    def test_serializer_read_only_fields_ignored_on_input(self):
        """Users shouldn't be able to forge calculated amounts or status via input data."""
        malicious_data = {
            "user_id": self.user.id,
            "loan_type": Loan.COMMERCIAL,
            "amount": "200000.00",
            "interest_rate": "19.00",
            "collateral_type": Loan.HOUSE,
            # Forged fields
            "monthly_payment": "1.00",
            "status": "approved",
            "approval_date": timezone.now()
        }
        serializer = LoanSerializer(data=malicious_data)
        self.assertTrue(serializer.is_valid())
        
        # Save it to check if fields revert to models defaults/calculations
        loan = serializer.save()
        self.assertEqual(loan.status, Loan.PENDING)  # Overrode the "approved" injection
        self.assertNotEqual(loan.monthly_payment, Decimal("1.00"))  # Calculated correctly instead


class LoanAPITestCase(APITestCase):
    """Integration API tests for loan endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="apiclient", 
            email="api@example.com", 
            password="apipassword123"
        )
        # Assuming you're hitting an endpoint wired to a ModelViewSet named 'loan-list'
        self.url = "/api/loans/" 

    def test_unauthenticated_user_cannot_apply(self):
        """Ensure security permissions protect the route."""
        data = {
            "loan_type": Loan.SOCIAL,
            "amount": "500000.00",
            "interest_rate": "17.00",
            "collateral_type": Loan.OTHER
        }
        response = self.client.post(self.url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_apply_successfully(self):
        """Ensure authenticated flow updates appropriately."""
        self.client.login(username="apiclient", password="apipassword123")
        
        data = {
            "loan_type": Loan.CONSTRUCTION,
            "amount": "150000.00",
            "interest_rate": "18.00",
            "collateral_type": Loan.HOUSE
        }
        response = self.client.post(self.url, data, format="json")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "pending")
        self.assertEqual(response.data["loan_type_display"], "Construction Loan")
        # Ensure the view automatically tied request.user to user_id
        self.assertIsNotNone(response.data["user_id"])