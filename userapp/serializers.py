# from django.contrib.auth.models import User
# from rest_framework import serializers 
# from rest_framework_simplejwt.serializers import  TokenObtainPairSerializer
# import datetime

# class UserSerializer (serializers.Serializer):
#     username =serializers.CharField()

# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer) :
#     @classmethod 
#     def get_token(cls,user):

#         User.objects.filter(id=user.id).update(
#             last_login=datetime.datetime.now()
#         ) 
#         token=super().get_token(user)
#         token["full_name"] =f"{user.first_name}{user.last_name}"
#         token ["email"] =user.email
#         return token 
from rest_framework import serializers
from userapp.models import User, LinkedBankAccount, Notification, PasswordResetCode
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import datetime
import re


class SocialAuthSerializer(serializers.Serializer):
    """Used for Continue with Google or Continue with Apple."""
    provider = serializers.ChoiceField(
        choices=[('google', 'Google'), ('apple', 'Apple')],
        help_text='Social provider: google or apple',
    )
    id_token = serializers.CharField(
        help_text='The ID token received from Google or Apple after the user authenticates on the frontend',
    )


class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    """Accepts email or phone number + password."""
    identifier = serializers.CharField(help_text='Email address or phone number')
    password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    """Step 1 — provide email or phone to receive a verification code."""
    identifier = serializers.CharField(help_text='Email address or phone number')
    channel = serializers.ChoiceField(
        choices=[('email', 'Email'), ('phone', 'Phone')],
        help_text='Choose where to receive the verification code',
    )

    def validate(self, attrs):
        identifier = attrs['identifier']
        channel = attrs['channel']
        user = (
            User.objects.filter(email=identifier).first() or
            User.objects.filter(phone_number=identifier).first()
        )
        if not user:
            raise serializers.ValidationError({'identifier': 'No account found with this email or phone number.'})
        if channel == 'phone' and not user.phone_number:
            raise serializers.ValidationError({'channel': 'This account has no phone number registered.'})
        attrs['user'] = user
        return attrs


class VerifyResetCodeSerializer(serializers.Serializer):
    """Step 2 — submit the 6-digit verification code."""
    identifier = serializers.CharField(help_text='Email address or phone number')
    code = serializers.CharField(max_length=6, min_length=6)

    def validate(self, attrs):
        identifier = attrs['identifier']
        user = (
            User.objects.filter(email=identifier).first() or
            User.objects.filter(phone_number=identifier).first()
        )
        if not user:
            raise serializers.ValidationError({'identifier': 'No account found.'})
        reset_code = PasswordResetCode.objects.filter(
            user=user, code=attrs['code'], is_used=False
        ).order_by('-created_at').first()
        if not reset_code or not reset_code.is_valid():
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})
        attrs['user'] = user
        attrs['reset_code'] = reset_code
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    """Step 3 — set new password after code is verified."""
    identifier = serializers.CharField(help_text='Email address or phone number')
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError('Password must be at least 8 characters.')
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError('Password must contain at least one number.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        identifier = attrs['identifier']
        user = (
            User.objects.filter(email=identifier).first() or
            User.objects.filter(phone_number=identifier).first()
        )
        if not user:
            raise serializers.ValidationError({'identifier': 'No account found.'})
        reset_code = PasswordResetCode.objects.filter(
            user=user, code=attrs['code'], is_used=False
        ).order_by('-created_at').first()
        if not reset_code or not reset_code.is_valid():
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})
        attrs['user'] = user
        attrs['reset_code'] = reset_code
        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number', 'profile_picture', 'user_type']


class PersonalInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'full_name', 'national_id', 'phone_number', 'address', 'email', 'account_number']
        read_only_fields = ['id', 'full_name', 'email']

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        # Keep full_name in sync whenever first or last name changes
        instance.full_name = f'{instance.first_name} {instance.last_name}'.strip()
        instance.save()
        return instance


class LinkedBankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkedBankAccount
        fields = ['id', 'bank_name', 'account_holder_name', 'account_number', 'is_default', 'created_at']
        read_only_fields = ['id', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'status', 'created_at']
        read_only_fields = ['id', 'title', 'message', 'notification_type', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    re_enter_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'password', 're_enter_password', 'created_on']
        read_only_fields = ['id', 'created_on']
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['re_enter_password']:
            raise serializers.ValidationError(
                {'re_enter_password': 'Passwords do not match.'}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop('re_enter_password')
        return User.objects.create_user(**validated_data)
        

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        user.last_login = datetime.datetime.now()
        user.save(update_fields=['last_login'])
        token = super().get_token(user)
        # Add custom claims
        token["first_name"] = user.first_name
        token["last_name"] = user.last_name
        token["full_name"] = user.full_name
        token["email"] = user.email
        token["phone_number"] = user.phone_number
        token["user_type"] = user.user_type
        return token