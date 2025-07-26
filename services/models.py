# services/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Service(models.Model):
    """
    Service offerings with flexible pricing models
    """
    
    PRICING_MODEL_CHOICES = [
        ('fixed', 'Fixed'),
        ('tiered', 'Tiered'),
        ('custom', 'Custom'),
        ('hourly', 'Hourly'),
        ('per-page', 'Per Page'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    
    # Categorization
    category = models.CharField(max_length=100)
    subcategory = models.CharField(max_length=100, blank=True)
    
    # Content fields
    description = models.TextField()
    short_description = models.TextField(blank=True)
    
    # Media fields
    img_url = models.TextField(blank=True)
    banner_url = models.TextField(blank=True)
    icon_url = models.TextField(blank=True)
    
    # Pricing fields
    pricing_model = models.CharField(
        max_length=20,
        choices=PRICING_MODEL_CHOICES
    )
    starting_at = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        blank=True,
        null=True
    )
    currency = models.CharField(max_length=10, default='KSH')
    timeline = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Estimated delivery timeline"
    )
    
    # Status fields
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'service'
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['sort_order', '-date_created']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category']),
            models.Index(fields=['featured']),
            models.Index(fields=['active']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ServicePricingTier(models.Model):
    """
    Pricing tiers for services (Essential, Growth, Premium packages)
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='pricing_tiers'
    )
    
    # Tier details
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='KSH')
    unit = models.CharField(
        max_length=50,
        help_text="Unit of pricing (project, hour, page, etc.)"
    )
    estimated_delivery = models.CharField(max_length=50, blank=True)
    recommended = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'service_pricing_tier'
        verbose_name = 'Service Pricing Tier'
        verbose_name_plural = 'Service Pricing Tiers'
        ordering = ['service', 'sort_order']
        indexes = [
            models.Index(fields=['service']),
            models.Index(fields=['recommended']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.name}"


class ServiceFeature(models.Model):
    """
    Features that can be included in different pricing tiers
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Feature details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon_class = models.CharField(
        max_length=50, 
        blank=True,
        help_text="CSS class for feature icon"
    )
    category = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Group features by category"
    )
    included = models.BooleanField(default=True)
    
    # Many-to-many relationship with pricing tiers
    pricing_tiers = models.ManyToManyField(
        ServicePricingTier,
        through='PricingTierFeature',
        related_name='features'
    )
    
    class Meta:
        db_table = 'service_feature'
        verbose_name = 'Service Feature'
        verbose_name_plural = 'Service Features'
        ordering = ['category', 'title']
    
    def __str__(self):
        return self.title


class PricingTierFeature(models.Model):
    """
    Many-to-many relationship between ServicePricingTier and ServiceFeature
    """
    
    pricing_tier = models.ForeignKey(
        ServicePricingTier,
        on_delete=models.CASCADE
    )
    feature = models.ForeignKey(
        ServiceFeature,
        on_delete=models.CASCADE
    )
    
    class Meta:
        db_table = 'pricingtier_feature'
        unique_together = ('pricing_tier', 'feature')
        verbose_name = 'Pricing Tier Feature'
        verbose_name_plural = 'Pricing Tier Features'
    
    def __str__(self):
        return f"{self.pricing_tier.name} - {self.feature.title}"


class ServiceFAQ(models.Model):
    """
    Frequently asked questions for services
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='faqs'
    )
    
    # FAQ content
    question = models.TextField()
    answer = models.TextField()
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'service_faq'
        verbose_name = 'Service FAQ'
        verbose_name_plural = 'Service FAQs'
        ordering = ['service', 'sort_order']
        indexes = [
            models.Index(fields=['service']),
        ]
    
    def __str__(self):
        return f"FAQ: {self.question[:50]}..."


class ServiceProcessStep(models.Model):
    """
    Process steps for how the service is delivered
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='process_steps'
    )
    
    # Step details
    step_order = models.IntegerField()
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon_class = models.CharField(max_length=50, blank=True)
    
    class Meta:
        db_table = 'service_process_step'
        verbose_name = 'Service Process Step'
        verbose_name_plural = 'Service Process Steps'
        ordering = ['service', 'step_order']
        indexes = [
            models.Index(fields=['service']),
            models.Index(fields=['step_order']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - Step {self.step_order}: {self.title}"


class ServiceDeliverable(models.Model):
    """
    What the client receives upon service completion
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='deliverables'
    )
    
    # Deliverable details
    description = models.TextField()
    icon_class = models.CharField(max_length=50, blank=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'service_deliverable'
        verbose_name = 'Service Deliverable'
        verbose_name_plural = 'Service Deliverables'
        ordering = ['service', 'sort_order']
        indexes = [
            models.Index(fields=['service']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.description[:50]}..."


class ServiceTool(models.Model):
    """
    Tools and technologies used in service delivery
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='tools'
    )
    
    # Tool details
    tool_name = models.CharField(max_length=100)
    tool_url = models.URLField(blank=True)
    icon_url = models.TextField(blank=True)
    
    class Meta:
        db_table = 'service_tool'
        verbose_name = 'Service Tool'
        verbose_name_plural = 'Service Tools'
        ordering = ['service', 'tool_name']
        indexes = [
            models.Index(fields=['service']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.tool_name}"


class ServicePopularUseCase(models.Model):
    """
    Popular use cases for the service
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='popular_usecases'
    )
    
    # Use case details
    use_case = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    class Meta:
        db_table = 'service_popular_usecase'
        verbose_name = 'Service Popular Use Case'
        verbose_name_plural = 'Service Popular Use Cases'
        ordering = ['service', 'use_case']
        indexes = [
            models.Index(fields=['service']),
        ]
    
    def __str__(self):
        return f"{self.service.name} - {self.use_case}"