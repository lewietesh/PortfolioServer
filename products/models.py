# products/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings


class Product(models.Model):
    """
    Digital products (templates, themes, tools, etc.)
    Separate from services - these are ready-made digital assets
    """
    
    TYPE_CHOICES = [
        ('website_template', 'Website Template'),
        ('web_app', 'Web Application'),
        ('component', 'Component'),
        ('theme', 'Theme'),
        ('plugin', 'Plugin'),
        ('tool', 'Tool'),
    ]
    
    LICENSE_CHOICES = [
        ('single_use', 'Single Use'),
        ('multi_use', 'Multi Use'),
        ('unlimited', 'Unlimited'),
        ('open_source', 'Open Source'),
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
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Content fields
    description = models.TextField()
    short_description = models.TextField(blank=True)
    
    # Relationships
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_products',
        limit_choices_to={'role__in': ['developer', 'admin']}
    )
    base_project = models.ForeignKey(
        'projects.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='derived_products',
        help_text="Original project this product was created from"
    )
    
    # Media fields
    image_url = models.TextField(blank=True)
    
    # Pricing fields
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10, default='KSH')
    
    # Product links
    demo_url = models.TextField(blank=True)
    download_url = models.TextField(blank=True)
    repository_url = models.TextField(blank=True)
    documentation_url = models.TextField(blank=True)
    
    # Status fields
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    
    # Metrics
    download_count = models.IntegerField(default=0)
    
    # Product details
    version = models.CharField(max_length=20, default='1.0.0')
    license_type = models.CharField(
        max_length=20,
        choices=LICENSE_CHOICES,
        default='single_use'
    )
    requirements = models.TextField(blank=True)
    installation_notes = models.TextField(blank=True)
    
    # Relationships with shared models
    tags = models.ManyToManyField(
        'blog.Tag',
        through='ProductTag',
        related_name='products',
        blank=True
    )
    technologies = models.ManyToManyField(
        'projects.Technology',
        through='ProductTechnology',
        related_name='products',
        blank=True
    )
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['category', 'active']),
            models.Index(fields=['featured', 'active']),
            models.Index(fields=['creator']),
            models.Index(fields=['base_project']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductGalleryImage(models.Model):
    """
    Gallery images for products (screenshots, previews)
    """
    
    id = models.AutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    image_url = models.TextField()
    alt_text = models.CharField(max_length=255, blank=True)
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'product_gallery_image'
        verbose_name = 'Product Gallery Image'
        verbose_name_plural = 'Product Gallery Images'
        ordering = ['product', 'sort_order']
        indexes = [
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - Image {self.sort_order}"


class ProductTechnology(models.Model):
    """
    Many-to-many relationship between Product and Technology
    """
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    technology = models.ForeignKey(
        'projects.Technology',
        on_delete=models.CASCADE
    )
    
    class Meta:
        db_table = 'product_technology'
        unique_together = ('product', 'technology')
        verbose_name = 'Product Technology'
        verbose_name_plural = 'Product Technologies'
    
    def __str__(self):
        return f"{self.product.name} - {self.technology.name}"


class ProductTag(models.Model):
    """
    Many-to-many relationship between Product and Tag
    """
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    tag = models.ForeignKey(
        'blog.Tag',
        on_delete=models.CASCADE
    )
    
    class Meta:
        db_table = 'product_tag'
        unique_together = ('product', 'tag')
        verbose_name = 'Product Tag'
        verbose_name_plural = 'Product Tags'
    
    def __str__(self):
        return f"{self.product.name} - {self.tag.name}"


class ProductPurchase(models.Model):
    """
    Product purchases and licensing tracking
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='purchases'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_purchases',
        limit_choices_to={'role': 'client'}
    )
    
    # Purchase details
    purchase_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=10)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Download tracking
    download_count = models.IntegerField(default=0)
    download_limit = models.IntegerField(blank=True, null=True)
    
    # License information
    license_key = models.CharField(max_length=255, unique=True, blank=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    
    # Payment information
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'product_purchase'
        verbose_name = 'Product Purchase'
        verbose_name_plural = 'Product Purchases'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['status']),
            models.Index(fields=['product']),
        ]
    
    def __str__(self):
        return f"{self.product.name} purchased by {self.client.email}"


class ProductReview(models.Model):
    """
    Product reviews and ratings from customers
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationships
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='product_reviews',
        limit_choices_to={'role': 'client'}
    )
    
    # Review content
    rating = models.IntegerField(help_text="Rating from 1-5")
    review_text = models.TextField(blank=True)
    
    # Moderation
    approved = models.BooleanField(default=False)
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'product_review'
        verbose_name = 'Product Review'
        verbose_name_plural = 'Product Reviews'
        ordering = ['-date_created']
        unique_together = ('product', 'client')  # One review per customer per product
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['approved']),
        ]
    
    def __str__(self):
        return f"Review by {self.client.email} for {self.product.name}"


class ProductUpdate(models.Model):
    """
    Product updates and changelogs
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='updates'
    )
    
    # Update details
    version = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    description = models.TextField()
    download_url = models.TextField(blank=True)
    is_major = models.BooleanField(
        default=False,
        help_text="Major version update vs minor update"
    )
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'product_update'
        verbose_name = 'Product Update'
        verbose_name_plural = 'Product Updates'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['version']),
        ]
    
    def __str__(self):
        return f"{self.product.name} v{self.version} - {self.title}"