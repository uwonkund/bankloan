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
class UserManager(BaseUserManager):

    def create_user(self,email, full_name, phone_number,password=None, **extra_fields):
        """
        Creates and saves a User with the given email and password.
        """

        user = self.model(
            email=email,
            full_name=full_name,
            phone_number=phone_number,
            **extra_fields,
        )
        user.set_password(password)
        print(user.set_password(password))
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email,full_name, phone_number, password=None, **extra_fields
    ):
        """
        Creates and saves a admin with the given email and password.
        """
        user = self.create_user(
            email=email,
            full_name=full_name,
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
    first_name=None
    last_name=None
    email=models.EmailField(_("email address"), unique=True)
    full_name=models.CharField(_("full name"),max_length=255)
    phone_number = models.CharField(
        _("phone number"), max_length=255, unique=True, validators=[
            MinLengthValidator(limit_value=10),
            MaxLengthValidator(limit_value=13)
        ]
    )
    is_active = models.BooleanField(_("is active"), default=False)
    user_type = models.CharField(
        _("user type"), max_length=50, choices=USER_TYPES_CHOICES, default=USER
    )
    # a admin user; non super-user
    is_staff = models.BooleanField(_("staff"), default=False)
    is_first_login = models.BooleanField(_("staff"), default=True)
    is_admin = models.BooleanField(_("admin"), default=False)  # a admin
    created_on = models.DateTimeField(_("created on"), auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = _("email",)
    REQUIRED_FIELDS = ["full_name","phone_number"]



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
