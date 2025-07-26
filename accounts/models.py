# accounts/models.py
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone


# Signal to automatically create ClientProfile for client users
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password"""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for system authentication
    Supports three user types: developers, admin, and clients
    """
    
    ROLE_CHOICES = [
        ('developer', 'Developer'),
        ('admin', 'Admin'),
        ('client', 'Client'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    email = models.EmailField(unique=True)
    
    # Personal information
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    
    # Contact information
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(
        validators=[phone_regex], 
        max_length=20, 
        blank=True
    )
    
    # Role and permissions
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='client'
    )
    
    # Django required fields
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    # Manager and authentication
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Return the user's full name"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def save(self, *args, **kwargs):
        """Override save to set staff status based on role"""
        if self.role in ['developer', 'admin']:
            self.is_staff = True
        else:
            self.is_staff = False
        super().save(*args, **kwargs)


class ClientProfile(models.Model):
    """
    Extended profile for users with 'client' role
    Contains essential business information for external customers
    """
    
    # One-to-One relationship with User
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='client_profile'
    )
    
    # Essential business fields
    company_name = models.CharField(max_length=255, blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    # Financial tracking
    account_balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0.00
    )
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client'
        verbose_name = 'Client Profile'
        verbose_name_plural = 'Client Profiles'
        ordering = ['-date_created']
    
    def __str__(self):
        return self.company_name or self.user.full_name


# Signal to automatically create ClientProfile for client users
@receiver(post_save, sender=User)
def create_client_profile(sender, instance, created, **kwargs):
    """Automatically create ClientProfile when User with role 'client' is created"""
    if instance.role == 'client':
        ClientProfile.objects.get_or_create(user=instance)