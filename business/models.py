# business/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.conf import settings


class Order(models.Model):
    """
    Orders for services or products
    Links clients to their purchases
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_orders',
        limit_choices_to={'role': 'client'}
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    pricing_tier = models.ForeignKey(
        'services.ServicePricingTier',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    
    # Financial fields
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='KSH')
    
    # Status fields
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    
    # Payment information
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    
    # Additional fields
    notes = models.TextField(blank=True)
    due_date = models.DateField(blank=True, null=True)
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'order'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"Order {self.id[:8]} - {self.client.email}"


class Testimonial(models.Model):
    """
    Client testimonials for social proof
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_testimonials',
        limit_choices_to={'role': 'client'}
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        help_text="Link to specific project if applicable"
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonials',
        help_text="Link to specific service if applicable"
    )
    
    # Content fields
    content = models.TextField()
    rating = models.IntegerField(
        blank=True,
        null=True,
        help_text="Rating from 1-5"
    )
    
    # Moderation fields
    featured = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'testimonial'
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['featured']),
            models.Index(fields=['approved']),
        ]
    
    def __str__(self):
        return f"Testimonial by {self.client.email}"


class Notification(models.Model):
    """
    System notifications for admin users
    """
    
    TYPE_CHOICES = [
        ('order', 'Order'),
        ('contact', 'Contact'),
        ('system', 'System'),
        ('payment', 'Payment'),
        ('review', 'Review'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content fields
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    
    # Status fields
    is_read = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    # Generic relationship fields
    resource_id = models.CharField(max_length=36, blank=True)
    resource_type = models.CharField(max_length=50, blank=True)
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_read']),
            models.Index(fields=['type']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.type.title()} notification: {self.title}"


class ContactMessage(models.Model):
    """
    Contact form submissions for lead capture
    """
    
    SOURCE_CHOICES = [
        ('website', 'Website'),
        ('whatsapp', 'WhatsApp'),
        ('referral', 'Referral'),
        ('social_media', 'Social Media'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Contact information
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Message content
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    
    # Tracking fields
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default='website'
    )
    is_read = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'contact_message'
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['is_read']),
            models.Index(fields=['replied']),
            models.Index(fields=['priority']),
            models.Index(fields=['source']),
        ]
    
    def __str__(self):
        return f"Contact from {self.name} - {self.subject}"

class Payment(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='KSH')
    method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default='pending')  # paid, failed, refunded
    notes = models.TextField(blank=True)
    date_created = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'payment'
        ordering = ['-date_created']

    def __str__(self):
        return f"{self.order_id} - {self.status}"
