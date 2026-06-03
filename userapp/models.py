from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext as _
from django.core.validators import MinLengthValidator, MaxLengthValidator

# class Customer(models.Model):
#     name = models.CharField(max_length=100)
#     email = models.EmailField(unique=True)
#     phone = models.CharField(max_length=20)
#     address = models.TextField()

#     def _str_(self):
#         return self.name
# class Bank_admin(models.Model):
#     name = models.CharField(max_length=100)
#     email = models.EmailField(unique=True)
#     phone = models.CharField(max_length=20)

#     def _str_(self):
#         return self.name    
class UserManager(BaseUserManager):

    def create_user(self, email, first_name, last_name, phone_number=None, password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            full_name=f'{first_name} {last_name}'.strip(),
            phone_number=phone_number,
            is_active=True,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email, first_name, last_name, phone_number=None, password=None, **extra_fields
    ):
        """
        Creates and saves a admin with the given email and password.
        """
        user = self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            password=password,
            **extra_fields,
        )

        user.is_active = True
        user.is_staff = True
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractUser, PermissionsMixin):
    OWNER='OWNER'
    CHECKER='CHECKER'
    USER='USER'
    ADMIN='ADMIN'
    USER_TYPES_CHOICES=[ 
    (OWNER, 'Owner'),
    (CHECKER,'Checker'),
    (USER,'User'),
    (ADMIN,'Admin')
    ]

    username=None
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email=models.EmailField(_("email address"), unique=True)
    full_name=models.CharField(_("full name"),max_length=255, blank=True)
    phone_number = models.CharField(
        _("phone number"), max_length=255, unique=True, blank=True, null=True, validators=[
            MinLengthValidator(limit_value=10),
            MaxLengthValidator(limit_value=13)
        ]
    )
    is_active = models.BooleanField(_("is active"), default=True)
    user_type = models.CharField(
        _("user type"), max_length=50, choices=USER_TYPES_CHOICES, default=USER
    )
    # a admin user; non super-user
    is_staff = models.BooleanField(_("staff"), default=False)
    is_first_login = models.BooleanField(_("staff"), default=True)
    is_admin = models.BooleanField(_("admin"), default=False)  # a admin
    profile_picture = models.ImageField(
        _("profile picture"), upload_to='profile_pictures/', null=True, blank=True
    )
    national_id = models.CharField(_("national ID"), max_length=50, blank=True, null=True)
    address = models.TextField(_("address"), blank=True, null=True)
    account_number = models.CharField(_("account number"), max_length=20, blank=True, null=True, unique=True)
    created_on = models.DateTimeField(_("created on"), auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]



    def get_short_name(self):
        # The user is identified by their email address
        return self.full_name

    def __str__(self):  # __unicode__ on Python 2O
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

# Create your models here.


class LinkedBankAccount(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='linked_bank_accounts'
    )
    bank_name = models.CharField(_("bank name"), max_length=100)
    account_holder_name = models.CharField(_("account holder name"), max_length=255)
    account_number = models.CharField(_("account number"), max_length=30)
    is_default = models.BooleanField(_("is default"), default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Only one default account per user
        if self.is_default:
            LinkedBankAccount.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.bank_name} — {self.account_number} ({self.user.email})'


class Notification(models.Model):
    UNREAD = 'unread'
    READ = 'read'
    STATUS_CHOICES = [
        (UNREAD, 'Unread'),
        (READ, 'Read'),
    ]

    INFO = 'info'
    SUCCESS = 'success'
    WARNING = 'warning'
    TYPE_CHOICES = [
        (INFO, 'Info'),
        (SUCCESS, 'Success'),
        (WARNING, 'Warning'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(_("title"), max_length=255)
    message = models.TextField(_("message"))
    notification_type = models.CharField(
        _("type"), max_length=10, choices=TYPE_CHOICES, default=INFO
    )
    status = models.CharField(
        _("status"), max_length=10, choices=STATUS_CHOICES, default=UNREAD
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.notification_type.upper()}] {self.title} — {self.user.email}'


class PasswordResetCode(models.Model):
    EMAIL = 'email'
    PHONE = 'phone'
    CHANNEL_CHOICES = [
        (EMAIL, 'Email'),
        (PHONE, 'Phone'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_codes')
    code = models.CharField(max_length=6)
    channel = models.CharField(max_length=5, choices=CHANNEL_CHOICES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()

    def __str__(self):
        return f'Reset code for {self.user.email} via {self.channel}'
