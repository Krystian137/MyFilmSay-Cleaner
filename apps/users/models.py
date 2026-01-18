from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class RoleEnum(models.TextChoices):
    USER = "user", "User"
    MODERATOR = "moderator", "Moderator"
    ADMIN = "admin", "Admin"


class UserManager(BaseUserManager):
    """Custom manager for User model"""

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not name:
            raise ValueError('Users must have a name')

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('role', RoleEnum.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name="Email Address")
    name = models.CharField(max_length=255, verbose_name="Full Name")
    role = models.CharField(
        max_length=20,
        choices=RoleEnum.choices,
        default=RoleEnum.USER,
        verbose_name="User Role"
    )
    is_active = models.BooleanField(default=True, verbose_name="Active Status")
    is_staff = models.BooleanField(default=False, verbose_name="Staff Status")
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Date Joined")
    last_login = models.DateTimeField(blank=True, null=True, verbose_name="Last Login")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def is_admin(self):
        return self.role == RoleEnum.ADMIN

    @property
    def is_moderator(self):
        return self.role == RoleEnum.MODERATOR or self.is_admin

    @property
    def is_regular_user(self):
        return self.role == RoleEnum.USER