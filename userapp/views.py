import random
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework import generics, viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from userapp.serializers import (
    CustomTokenObtainPairSerializer, UserSerializer, LoginResponseSerializer,
    LoginSerializer, SocialAuthSerializer, UserProfileSerializer, PersonalInfoSerializer,
    LinkedBankAccountSerializer, NotificationSerializer,
    ForgotPasswordSerializer, VerifyResetCodeSerializer, ResetPasswordSerializer,
)
from userapp.models import User, LinkedBankAccount, Notification, PasswordResetCode
from payment.models import Payment
from payment.serializers import DashboardPaymentHistorySerializer


class SocialAuthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Continue with Google / Apple',
        tags=['User Management'],
        description=(
            'Sign up or log in using Google or Apple.\n\n'
            '**How it works:**\n'
            '1. Frontend triggers Google or Apple OAuth flow and receives an `id_token`\n'
            '2. Frontend sends `provider` (`google` or `apple`) and `id_token` to this endpoint\n'
            '3. Backend verifies the token, creates the account if new, and returns JWT tokens\n\n'
            '**Google:** Use Google Sign-In SDK to get the `id_token`\n'
            '**Apple:** Use Sign in with Apple SDK to get the `id_token`\n\n'
            'Returns JWT `access` and `refresh` tokens same as regular login.'
        ),
        request=SocialAuthSerializer,
        responses={
            200: LoginResponseSerializer,
            400: OpenApiResponse(description='Invalid or expired token'),
        },
    )
    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data['provider']
        id_token = serializer.validated_data['id_token']

        user_info = self._verify_token(provider, id_token)
        if not user_info:
            return Response(
                {'detail': 'Invalid or expired token. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = user_info.get('email')
        first_name = user_info.get('first_name', '')
        last_name = user_info.get('last_name', '')

        if not email:
            return Response(
                {'detail': 'Could not retrieve email from provider.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                'full_name': f'{first_name} {last_name}'.strip(),
                'is_active': True,
            },
        )

        refresh = RefreshToken.for_user(user)
        refresh['first_name'] = user.first_name
        refresh['last_name'] = user.last_name
        refresh['full_name'] = user.full_name
        refresh['email'] = user.email
        refresh['phone_number'] = user.phone_number
        refresh['user_type'] = user.user_type

        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'is_new_user': created,
        }, status=status.HTTP_200_OK)

    def _verify_token(self, provider, id_token):
        try:
            if provider == 'google':
                return self._verify_google_token(id_token)
            elif provider == 'apple':
                return self._verify_apple_token(id_token)
        except Exception:
            return None

    def _verify_google_token(self, id_token):
        import urllib.request
        import json
        url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
        if data.get('error'):
            return None
        return {
            'email': data.get('email'),
            'first_name': data.get('given_name', ''),
            'last_name': data.get('family_name', ''),
        }

    def _verify_apple_token(self, id_token):
        import jwt as pyjwt
        import urllib.request
        import json
        with urllib.request.urlopen('https://appleid.apple.com/auth/keys') as response:
            apple_keys = json.loads(response.read())
        header = pyjwt.get_unverified_header(id_token)
        key = next((k for k in apple_keys['keys'] if k['kid'] == header['kid']), None)
        if not key:
            return None
        public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
        data = pyjwt.decode(
            id_token,
            public_key,
            algorithms=['RS256'],
            audience='com.yourapp.bundleid',
        )
        name = data.get('name', {})
        return {
            'email': data.get('email'),
            'first_name': name.get('firstName', '') if isinstance(name, dict) else '',
            'last_name': name.get('lastName', '') if isinstance(name, dict) else '',
        }


class SignUpView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Sign Up',
        tags=['User Management'],
        description='Register a new user. Required fields: first_name, last_name, email, password, re_enter_password.',
        request=UserSerializer,
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation errors (e.g. email exists, passwords don't match)"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Sign up failed. Please check the errors below.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        self.perform_create(serializer)
        return Response({
            'success': True,
            'message': 'Account created successfully! Please log in.',
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Login',
        tags=['User Management'],
        description=(
            'Authenticate using email and password.\n\n'
            'Returns JWT access and refresh tokens with user claims.'
        ),
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            401: OpenApiResponse(description='Invalid credentials'),
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Login failed. Please check the errors below.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        identifier = serializer.validated_data['email']
        password = serializer.validated_data['password']

        user = User.objects.filter(email=identifier).first()

        if not user or not user.check_password(password):
            return Response({
                'success': False,
                'message': 'Login unsuccessful. Invalid email or password.',
            }, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        refresh['first_name'] = user.first_name
        refresh['last_name'] = user.last_name
        refresh['full_name'] = user.full_name
        refresh['email'] = user.email
        refresh['phone_number'] = user.phone_number
        refresh['user_type'] = user.user_type

        return Response({
            'success': True,
            'message': f'Welcome back, {user.first_name}! You have successfully logged in.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


@extend_schema(
    summary='Refresh Token',
    tags=['User Management'],
    description='Provide a valid refresh token to get a new access token.',
)
class TokenRefreshView(TokenRefreshView):
    pass


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Forgot Password — Step 1: Select Channel & Send Code',
        tags=['User Management'],
        description=(
            '**Forgot Password Screen**\n\n'
            'User enters their registered email or phone number and selects '
            'where to receive the 6-digit verification code:\n\n'
            '- `email` — Send to your email\n'
            '- `phone` — Send to your phone\n\n'
            '**Request body:**\n'
            '```json\n'
            '{\n'
            '  "identifier": "user@email.com",\n'
            '  "channel": "email"\n'
            '}\n'
            '```\n\n'
            'On success a 6-digit code is sent to the chosen destination. '
            'Code expires in 10 minutes.'
        ),
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Verification code sent successfully'),
            400: OpenApiResponse(description='Account not found or invalid channel'),
        },
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        channel = serializer.validated_data['channel']

        code = str(random.randint(100000, 999999))
        PasswordResetCode.objects.create(
            user=user,
            code=code,
            channel=channel,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        if channel == 'email':
            send_mail(
                subject='Your Password Reset Verification Code',
                message=(
                    f'Hello {user.first_name},\n\n'
                    f'Your verification code is: {code}\n\n'
                    f'This code expires in 10 minutes.\n\n'
                    f'If you did not request a password reset, please ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            destination = user.email
        else:
            # Phone SMS integration (e.g. Twilio) goes here
            destination = user.phone_number

        return Response({
            'detail': f'Verification code sent to your {channel}.',
            'channel': channel,
            'destination': destination,
        }, status=status.HTTP_200_OK)


class VerifyResetCodeView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Forgot Password — Step 2: Enter Verification Code',
        tags=['User Management'],
        description=(
            '**Verification Code Screen**\n\n'
            'User enters the 6-digit code received on their email or phone.\n\n'
            '**Request body:**\n'
            '```json\n'
            '{\n'
            '  "identifier": "user@email.com",\n'
            '  "code": "123456"\n'
            '}\n'
            '```\n\n'
            'If valid, proceed to Step 3 to set a new password.'
        ),
        request=VerifyResetCodeSerializer,
        responses={
            200: OpenApiResponse(description='Code verified. Proceed to reset password.'),
            400: OpenApiResponse(description='Invalid or expired code'),
        },
    )
    def post(self, request):
        serializer = VerifyResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            {'detail': 'Code verified. You may now reset your password.'},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary='Forgot Password — Step 3: Set New Password',
        tags=['User Management'],
        description=(
            '**Create New Password Screen**\n\n'
            'User sets their new password after the code has been verified.\n\n'
            '**Request body:**\n'
            '```json\n'
            '{\n'
            '  "identifier": "user@email.com",\n'
            '  "code": "123456",\n'
            '  "new_password": "NewPass123",\n'
            '  "confirm_password": "NewPass123"\n'
            '}\n'
            '```\n\n'
            '**Password requirements:**\n'
            '- At least 8 characters\n'
            '- At least one uppercase letter\n'
            '- At least one number\n\n'
            'On success returns `{"detail": "Congratulations! Password changed!"}`.'
        ),
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description='Congratulations! Password changed!'),
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
        reset_code = serializer.validated_data['reset_code']

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])

        reset_code.is_used = True
        reset_code.save(update_fields=['is_used'])

        return Response(
            {'detail': 'Congratulations! Password changed!'},
            status=status.HTTP_200_OK,
        )


class HomeDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Home Dashboard',
        tags=['User Management'],
        description=(
            "Returns the logged-in user's profile, active loan summary "
            '(balance, loan token, monthly payment, next due date), and last 10 payments.'
        ),
        responses={200: OpenApiResponse(description='Dashboard data')},
    )
    def get(self, request):
        user = request.user
        profile = UserProfileSerializer(user, context={'request': request}).data

        active_loan = user.loans.filter(status='APPROVED').order_by('-created_at').first()

        loan_summary = None
        if active_loan:
            next_schedule = active_loan.payment_schedules.filter(
                is_paid=False
            ).order_by('due_date').first()

            remaining = active_loan.payment_schedules.filter(
                is_paid=False
            ).aggregate(total=Sum('total_due'))['total'] or 0

            loan_summary = {
                'loan_id': active_loan.id,
                'loan_type': active_loan.loan_type,
                'loan_token': f'LN-{active_loan.id:06d}',
                'current_balance': remaining,
                'monthly_payment': active_loan.monthly_payment,
                'next_due_date': next_schedule.due_date if next_schedule else None,
                'next_due_amount': next_schedule.total_due if next_schedule else None,
                'status': active_loan.status,
            }

        recent_payments = Payment.objects.filter(
            loan__user_id=user
        ).order_by('-payment_date')[:10]
        payment_history = DashboardPaymentHistorySerializer(recent_payments, many=True).data

        return Response({
            'profile': profile,
            'loan_summary': loan_summary,
            'payment_history': payment_history,
        }, status=status.HTTP_200_OK)


class UpdateProfilePictureView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Update Profile Picture',
        tags=['User Settings'],
        description="Upload or update the logged-in user's profile picture.",
        responses={200: UserProfileSerializer},
    )
    def patch(self, request):
        user = request.user
        file = request.FILES.get('profile_picture')
        if not file:
            return Response({'error': 'No file provided.'}, status=status.HTTP_400_BAD_REQUEST)
        user.profile_picture = file
        user.save()
        return Response(UserProfileSerializer(user, context={'request': request}).data)


class PersonalInfoView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Get Personal Information',
        tags=['User Settings'],
        description="Returns the logged-in user's personal info.",
        responses={200: PersonalInfoSerializer},
    )
    def get(self, request):
        serializer = PersonalInfoSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary='Update Personal Information',
        tags=['User Settings'],
        description='Update personal info: first_name, last_name, national_id, phone_number, address, account_number.',
        request=PersonalInfoSerializer,
        responses={
            200: PersonalInfoSerializer,
            400: OpenApiResponse(description='Validation error'),
        },
    )
    def patch(self, request):
        serializer = PersonalInfoSerializer(
            request.user, data=request.data, partial=True, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    list=extend_schema(summary='List Linked Bank Accounts', tags=['User Settings']),
    create=extend_schema(
        summary='Add Linked Bank Account',
        tags=['User Settings'],
        description='Link a new bank account. Set is_default=true to make it the default.',
    ),
    retrieve=extend_schema(summary='Get Linked Bank Account', tags=['User Settings']),
    update=extend_schema(summary='Update Linked Bank Account', tags=['User Settings']),
    partial_update=extend_schema(summary='Partially Update Linked Bank Account', tags=['User Settings']),
    destroy=extend_schema(summary='Remove Linked Bank Account', tags=['User Settings']),
)
class LinkedBankAccountViewSet(viewsets.ModelViewSet):
    serializer_class = LinkedBankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LinkedBankAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary='List Notifications',
        tags=['User Settings'],
        description='Returns all bank messages/notifications for the logged-in user.',
    ),
    retrieve=extend_schema(summary='Get Notification', tags=['User Settings']),
    partial_update=extend_schema(
        summary='Mark Notification as Read',
        tags=['User Settings'],
        description="Set status to 'read'.",
    ),
)
class NotificationViewSet(viewsets.GenericViewSet,
                          viewsets.mixins.ListModelMixin,
                          viewsets.mixins.RetrieveModelMixin,
                          viewsets.mixins.UpdateModelMixin):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)