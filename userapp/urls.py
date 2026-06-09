from django.urls import path, include
from rest_framework.routers import DefaultRouter
from userapp.views import (
    SocialAuthView, SignUpView, LoginView, TokenRefreshView,
    ForgotPasswordView, ResendCodeView, VerifyResetCodeView, ResetPasswordView,
    HomeDashboardView, UpdateProfilePictureView,
    PersonalInfoView, LinkedBankAccountViewSet, NotificationViewSet,
)
from userapp.admin_views import AdminDashboardView

router = DefaultRouter()
router.register(r'settings/bank-accounts', LinkedBankAccountViewSet, basename='linked-bank-account')
router.register(r'settings/notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Auth
    path('signup/', SignUpView.as_view(), name='signup'),
    path('social-auth/', SocialAuthView.as_view(), name='social_auth'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Forgot Password flow
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('forgot-password/resend/', ResendCodeView.as_view(), name='resend_code'),
    path('forgot-password/verify/', VerifyResetCodeView.as_view(), name='verify_reset_code'),
    path('forgot-password/reset/', ResetPasswordView.as_view(), name='reset_password'),

    # Dashboard
    path('home/', HomeDashboardView.as_view(), name='home_dashboard'),
    
    # Admin Dashboard
    path('admin/dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),

    # Profile
    path('profile/picture/', UpdateProfilePictureView.as_view(), name='update_profile_picture'),

    # Settings
    path('settings/personal-info/', PersonalInfoView.as_view(), name='personal_info'),
    path('', include(router.urls)),
]
