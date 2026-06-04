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
    email = serializers.EmailField(help_text='Email address')
    password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text='Your registered email address')

    def validate(self, attrs):
        user = User.objects.filter(email=attrs['email']).first()
        if not user:
            raise serializers.ValidationError(
                {'email': 'No account found with this email address.'}
            )
        attrs['user'] = user
        attrs['channel'] = 'email'
        return attrs


class VerifyResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text='Same email used in Step 1')
    code = serializers.CharField(
        max_length=6, min_length=6,
        help_text='6-digit verification code received via email'
    )

    def validate(self, attrs):
        user = User.objects.filter(email=attrs['email']).first()
        if not user:
            raise serializers.ValidationError({'email': 'No account found.'})
        reset_code = PasswordResetCode.objects.filter(
            user=user, code=attrs['code'], is_used=False
        ).order_by('-created_at').first()
        if not reset_code or not reset_code.is_valid():
            raise serializers.ValidationError({'code': 'Invalid or expired verification code.'})
        attrs['user'] = user
        attrs['reset_code'] = reset_code
        return attrs


class ResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text='Your registered email address')

    def validate(self, attrs):
        user = User.objects.filter(email=attrs['email']).first()
        if not user:
            raise serializers.ValidationError(
                {'email': 'No account found with this email address.'}
            )
        attrs['user'] = user
        attrs['channel'] = 'email'
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(help_text='Same email used in Steps 1 & 2')
    code = serializers.CharField(max_length=6, min_length=6, help_text='The verified 6-digit code')
    new_password = serializers.CharField(write_only=True, help_text='Min 8 chars, one uppercase, one number')
    confirm_password = serializers.CharField(write_only=True, help_text='Must match new_password')

    def validate_new_password(self, value):
        errors = []
        if len(value) < 8:
            errors.append('At least 8 characters.')
        if not re.search(r'[A-Z]', value):
            errors.append('At least one uppercase letter.')
        if not re.search(r'[0-9]', value):
            errors.append('At least one number.')
        if errors:
            raise serializers.ValidationError(errors)
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {'confirm_password': 'Passwords do not match.'}
            )
        user = User.objects.filter(email=attrs['email']).first()
        if not user:
            raise serializers.ValidationError({'email': 'No account found.'})
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