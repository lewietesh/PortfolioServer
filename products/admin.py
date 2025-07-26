# products/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg, Sum
from .models import (
    Product, ProductGalleryImage, ProductReview, ProductPurchase, 
    ProductTechnology, ProductTag, ProductUpdate
)


class ProductGalleryImageInline(admin.TabularInline):
    """
    Inline admin for product gallery images
    """
    model = ProductGalleryImage
    extra = 1
    fields = ['image_url', 'alt_text', 'sort_order', 'image_preview']
    readonly_fields = ['image_preview']
    ordering = ['sort_order']
    
    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 100px; max-height: 60px;" />',
                obj.image_url
            )
        return '-'
    image_preview.short_description = 'Preview'


class ProductTechnologyInline(admin.TabularInline):
    """
    Inline admin for product technologies
    """
    model = ProductTechnology
    extra = 1
    autocomplete_fields = ['technology']


class ProductTagInline(admin.TabularInline):
    """
    Inline admin for product tags
    """
    model = ProductTag
    extra = 1
    autocomplete_fields = ['tag']


class ProductUpdateInline(admin.TabularInline):
    """
    Inline admin for product updates
    """
    model = ProductUpdate
    extra = 0
    fields = ['version', 'title', 'description', 'is_major', 'date_created']
    readonly_fields = ['date_created']
    ordering = ['-date_created']


class ProductReviewInline(admin.TabularInline):
    """
    Inline admin for product reviews
    """
    model = ProductReview
    extra = 0
    readonly_fields = ['client', 'rating', 'review_text', 'date_created', 'approved']
    fields = ['client', 'rating', 'review_text', 'approved', 'date_created']
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        """Disable adding reviews through inline"""
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Admin interface for Product model
    """
    
    list_display = [
        'name',
        'category',
        'type_display',
        'price_display',
        'creator',
        'featured_display',
        'active_display',
        'download_count',
        'average_rating_display',
        'reviews_count',
        'date_created'
    ]
    list_filter = [
        'category',
        'type',
        'featured',
        'active',
        'license_type',
        'creator',
        'date_created',
        # Removed 'technologies' and 'tags' from list_filter since they have through models
    ]
    search_fields = ['name', 'description', 'short_description', 'category']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'id',
        'download_count',
        'date_created',
        'date_updated',
        'average_rating_display',
        'reviews_count',
        'total_revenue',
        'purchases_count'
    ]
    # Removed filter_horizontal for technologies and tags since they have through models
    raw_id_fields = ['creator', 'base_project']
    inlines = [
        ProductGalleryImageInline, 
        ProductTechnologyInline,  # Added for managing technologies
        ProductTagInline,         # Added for managing tags
        ProductUpdateInline, 
        ProductReviewInline
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'type', 'creator')
        }),
        ('Content', {
            'fields': ('short_description', 'description', 'image_url')
        }),
        ('Project & Requirements', {
            'fields': ('base_project', 'requirements', 'installation_notes'),
            'classes': ('collapse',)
        }),
        ('Pricing & License', {
            'fields': ('price', 'currency', 'license_type', 'version')
        }),
        ('URLs & Links', {
            'fields': ('demo_url', 'download_url', 'repository_url', 'documentation_url'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('featured', 'active')
        }),
        # Removed 'Relationships' fieldset since technologies and tags can't be in fieldsets with through models
        ('Statistics', {
            'fields': ('download_count', 'average_rating_display', 'reviews_count', 'purchases_count', 'total_revenue'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def type_display(self, obj):
        """Display product type with formatting"""
        return obj.get_type_display()
    type_display.short_description = 'Type'
    
    def price_display(self, obj):
        """Display price with currency"""
        if obj.price > 0:
            return format_html(
                '<strong>{} {}</strong>',
                obj.currency, obj.price
            )
        return format_html('<span style="color: green;">FREE</span>')
    price_display.short_description = 'Price'
    
    def featured_display(self, obj):
        """Display featured status"""
        if obj.featured:
            return format_html('<span style="color: gold;">⭐ Featured</span>')
        return '-'
    featured_display.short_description = 'Featured'
    
    def active_display(self, obj):
        """Display active status with color coding"""
        if obj.active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Inactive</span>')
    active_display.short_description = 'Status'
    
    def average_rating_display(self, obj):
        """Display average rating with stars"""
        approved_reviews = obj.reviews.filter(approved=True)
        if approved_reviews.exists():
            avg_rating = sum(review.rating for review in approved_reviews) / approved_reviews.count()
            stars = '⭐' * int(avg_rating)
            return format_html('{} {:.1f}', stars, avg_rating)
        return '-'
    average_rating_display.short_description = 'Rating'
    
    def reviews_count(self, obj):
        """Count of approved reviews"""
        return obj.reviews.filter(approved=True).count()
    reviews_count.short_description = 'Reviews'
    
    def purchases_count(self, obj):
        """Count of completed purchases"""
        return obj.purchases.filter(status='completed').count()
    purchases_count.short_description = 'Purchases'
    
    def total_revenue(self, obj):
        """Total revenue from purchases"""
        purchases = obj.purchases.filter(status='completed')
        revenue = sum(p.purchase_amount for p in purchases)
        if revenue > 0:
            return format_html('{} {:.2f}', obj.currency, revenue)
        return '-'
    total_revenue.short_description = 'Revenue'
    
    actions = ['feature_products', 'unfeature_products', 'activate_products', 'deactivate_products']
    
    def feature_products(self, request, queryset):
        """Feature selected products"""
        updated = queryset.update(featured=True)
        self.message_user(request, f"Successfully featured {updated} product(s).")
    feature_products.short_description = "Feature selected products"
    
    def unfeature_products(self, request, queryset):
        """Unfeature selected products"""
        updated = queryset.update(featured=False)
        self.message_user(request, f"Successfully unfeatured {updated} product(s).")
    unfeature_products.short_description = "Unfeature selected products"
    
    def activate_products(self, request, queryset):
        """Activate selected products"""
        updated = queryset.update(active=True)
        self.message_user(request, f"Successfully activated {updated} product(s).")
    activate_products.short_description = "Activate selected products"
    
    def deactivate_products(self, request, queryset):
        """Deactivate selected products"""
        updated = queryset.update(active=False)
        self.message_user(request, f"Successfully deactivated {updated} product(s).")
    deactivate_products.short_description = "Deactivate selected products"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related(
            'creator', 'base_project'
        ).prefetch_related('technologies', 'tags', 'reviews', 'purchases')


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductReview model
    """
    
    list_display = [
        'product_name',
        'client_name',
        'rating_display',
        'review_preview',
        'approved_display',
        'date_created'
    ]
    list_filter = [
        'rating',
        'approved',
        'date_created',
        'product__category'
    ]
    search_fields = [
        'review_text',
        'product__name',
        'client__email'
    ]
    readonly_fields = [
        'id',
        'date_created',
        'product_link',
        'client_link'
    ]
    raw_id_fields = ['product', 'client']
    
    fieldsets = (
        ('Review Details', {
            'fields': ('product_link', 'client_link', 'rating', 'review_text')
        }),
        ('Moderation', {
            'fields': ('approved',)
        }),
        ('Metadata', {
            'fields': ('id', 'date_created'),
            'classes': ('collapse',)
        }),
    )
    
    def product_name(self, obj):
        """Display product name with link"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}">{}</a>', url, obj.product.name)
        return '-'
    product_name.short_description = 'Product'
    
    def client_name(self, obj):
        """Display client name"""
        if obj.client:
            if obj.client.first_name or obj.client.last_name:
                return f"{obj.client.first_name} {obj.client.last_name}".strip()
            return obj.client.email
        return 'Anonymous'
    client_name.short_description = 'Client'
    
    def rating_display(self, obj):
        """Display rating with stars"""
        stars = '⭐' * obj.rating
        return format_html('{} ({})', stars, obj.rating)
    rating_display.short_description = 'Rating'
    
    def review_preview(self, obj):
        """Show truncated review text"""
        if obj.review_text:
            return (obj.review_text[:75] + '...') if len(obj.review_text) > 75 else obj.review_text
        return '-'
    review_preview.short_description = 'Review Preview'
    
    def approved_display(self, obj):
        """Display approval status with color coding"""
        if obj.approved:
            return format_html('<span style="color: green;">✓ Approved</span>')
        return format_html('<span style="color: red;">✗ Pending</span>')
    approved_display.short_description = 'Status'
    
    def product_link(self, obj):
        """Link to parent product"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.product.name)
        return '-'
    product_link.short_description = 'Product'
    
    def client_link(self, obj):
        """Link to client"""
        if obj.client:
            url = reverse('admin:accounts_user_change', args=[obj.client.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.client.email)
        return 'Anonymous'
    client_link.short_description = 'Client'
    
    actions = ['approve_reviews', 'reject_reviews', 'delete_spam']
    
    def approve_reviews(self, request, queryset):
        """Approve selected reviews"""
        updated = queryset.update(approved=True)
        self.message_user(request, f"Successfully approved {updated} review(s).")
    approve_reviews.short_description = "Approve selected reviews"
    
    def reject_reviews(self, request, queryset):
        """Reject selected reviews"""
        updated = queryset.update(approved=False)
        self.message_user(request, f"Successfully rejected {updated} review(s).")
    reject_reviews.short_description = "Reject selected reviews"
    
    def delete_spam(self, request, queryset):
        """Delete selected reviews (for spam)"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Successfully deleted {count} review(s).")
    delete_spam.short_description = "Delete selected reviews (spam)"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related('product', 'client').order_by('-date_created')


@admin.register(ProductPurchase)
class ProductPurchaseAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductPurchase model
    """
    
    list_display = [
        'product_name',
        'client_name',
        'purchase_amount_display',
        'status_display',
        'download_count',
        'download_limit',
        'license_key_preview',
        'date_created'
    ]
    list_filter = [
        'status',
        'currency',
        'date_created',
        'product__category',
        'payment_method'
    ]
    search_fields = [
        'product__name',
        'client__email',
        'license_key',
        'transaction_id'
    ]
    readonly_fields = [
        'id',
        'license_key',
        'date_created',
        'date_updated',
        'product_link',
        'client_link'
    ]
    raw_id_fields = ['product', 'client']
    
    fieldsets = (
        ('Purchase Details', {
            'fields': ('product_link', 'client_link', 'purchase_amount', 'currency', 'status')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'transaction_id'),
            'classes': ('collapse',)
        }),
        ('License & Downloads', {
            'fields': ('license_key', 'download_count', 'download_limit', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def product_name(self, obj):
        """Display product name with link"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}">{}</a>', url, obj.product.name)
        return '-'
    product_name.short_description = 'Product'
    
    def client_name(self, obj):
        """Display client name"""
        if obj.client:
            if obj.client.first_name or obj.client.last_name:
                return f"{obj.client.first_name} {obj.client.last_name}".strip()
            return obj.client.email
        return 'Anonymous'
    client_name.short_description = 'Client'
    
    def purchase_amount_display(self, obj):
        """Display purchase amount with currency"""
        return format_html(
            '<strong>{} {:.2f}</strong>',
            obj.currency, obj.purchase_amount
        )
    purchase_amount_display.short_description = 'Amount'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#ffc107',     # Yellow
            'completed': '#28a745',   # Green
            'failed': '#dc3545',      # Red
            'refunded': '#6c757d'     # Gray
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.status.title()
        )
    status_display.short_description = 'Status'
    
    def license_key_preview(self, obj):
        """Show truncated license key"""
        if obj.license_key:
            return f"{obj.license_key[:8]}..." if len(obj.license_key) > 8 else obj.license_key
        return '-'
    license_key_preview.short_description = 'License Key'
    
    def product_link(self, obj):
        """Link to parent product"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.product.name)
        return '-'
    product_link.short_description = 'Product'
    
    def client_link(self, obj):
        """Link to client"""
        if obj.client:
            url = reverse('admin:accounts_user_change', args=[obj.client.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.client.email)
        return 'Anonymous'
    client_link.short_description = 'Client'
    
    actions = ['mark_completed', 'mark_failed', 'mark_refunded']
    
    def mark_completed(self, request, queryset):
        """Mark selected purchases as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f"Successfully marked {updated} purchase(s) as completed.")
    mark_completed.short_description = "Mark selected purchases as completed"
    
    def mark_failed(self, request, queryset):
        """Mark selected purchases as failed"""
        updated = queryset.update(status='failed')
        self.message_user(request, f"Successfully marked {updated} purchase(s) as failed.")
    mark_failed.short_description = "Mark selected purchases as failed"
    
    def mark_refunded(self, request, queryset):
        """Mark selected purchases as refunded"""
        updated = queryset.update(status='refunded')
        self.message_user(request, f"Successfully marked {updated} purchase(s) as refunded.")
    mark_refunded.short_description = "Mark selected purchases as refunded"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related('product', 'client').order_by('-date_created')


@admin.register(ProductUpdate)
class ProductUpdateAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductUpdate model
    """
    
    list_display = [
        'product_name',
        'version',
        'title',
        'is_major_display',
        'date_created'
    ]
    list_filter = [
        'is_major',
        'date_created',
        'product__category'
    ]
    search_fields = [
        'title',
        'description',
        'version',
        'product__name'
    ]
    readonly_fields = [
        'id',
        'date_created',
        'product_link'
    ]
    raw_id_fields = ['product']
    
    fieldsets = (
        ('Update Details', {
            'fields': ('product_link', 'version', 'title', 'description')
        }),
        ('Release Information', {
            'fields': ('download_url', 'is_major')
        }),
        ('Metadata', {
            'fields': ('id', 'date_created'),
            'classes': ('collapse',)
        }),
    )
    
    def product_name(self, obj):
        """Display product name with link"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}">{}</a>', url, obj.product.name)
        return '-'
    product_name.short_description = 'Product'
    
    def is_major_display(self, obj):
        """Display major version indicator"""
        if obj.is_major:
            return format_html('<span style="color: red; font-weight: bold;">Major</span>')
        return format_html('<span style="color: blue;">Minor</span>')
    is_major_display.short_description = 'Update Type'
    
    def product_link(self, obj):
        """Link to parent product"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.product.name)
        return '-'
    product_link.short_description = 'Product'
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related('product').order_by('-date_created')


@admin.register(ProductGalleryImage)
class ProductGalleryImageAdmin(admin.ModelAdmin):
    """
    Admin interface for ProductGalleryImage model
    """
    
    list_display = [
        'product_name',
        'image_preview',
        'alt_text',
        'sort_order',
        'id'
    ]
    list_filter = [
        'product__category',
        'product__active'
    ]
    search_fields = [
        'product__name',
        'alt_text'
    ]
    readonly_fields = ['image_preview']
    raw_id_fields = ['product']
    ordering = ['product', 'sort_order']
    
    fieldsets = (
        ('Image Details', {
            'fields': ('product', 'image_url', 'alt_text', 'sort_order')
        }),
        ('Preview', {
            'fields': ('image_preview',),
            'classes': ('collapse',)
        }),
    )
    
    def product_name(self, obj):
        """Display product name with link"""
        if obj.product:
            url = reverse('admin:products_product_change', args=[obj.product.pk])
            return format_html('<a href="{}">{}</a>', url, obj.product.name)
        return '-'
    product_name.short_description = 'Product'
    
    def image_preview(self, obj):
        """Display image preview in admin"""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 120px; '
                'border: 1px solid #ddd; border-radius: 4px;" />',
                obj.image_url
            )
        return '-'
    image_preview.short_description = 'Image Preview'
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related('product')


# Custom admin site configuration
admin.site.site_header = "Portfolio Products Administration"
admin.site.site_title = "Products Admin"
admin.site.index_title = "Products Management Dashboard"


# Custom filters
class ProductRatingFilter(admin.SimpleListFilter):
    """
    Custom filter for products by average rating
    """
    title = 'average rating'
    parameter_name = 'rating'
    
    def lookups(self, request, model_admin):
        return (
            ('5', '5 stars'),
            ('4', '4+ stars'),
            ('3', '3+ stars'),
            ('2', '2+ stars'),
            ('1', '1+ stars'),
        )
    
    def queryset(self, request, queryset):
        if self.value():
            rating = int(self.value())
            # Filter products with average rating >= selected value
            product_ids = []
            for product in queryset:
                approved_reviews = product.reviews.filter(approved=True)
                if approved_reviews.exists():
                    avg_rating = sum(review.rating for review in approved_reviews) / approved_reviews.count()
                    if avg_rating >= rating:
                        product_ids.append(product.id)
            return queryset.filter(id__in=product_ids)
        return queryset


class ProductPriceRangeFilter(admin.SimpleListFilter):
    """
    Custom filter for products by price range
    """
    title = 'price range'
    parameter_name = 'price_range'
    
    def lookups(self, request, model_admin):
        return (
            ('free', 'Free (0)'),
            ('0-1000', 'KSh 0 - 1,000'),
            ('1000-5000', 'KSh 1,000 - 5,000'),
            ('5000-10000', 'KSh 5,000 - 10,000'),
            ('10000+', 'KSh 10,000+'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'free':
            return queryset.filter(price=0)
        elif self.value() == '0-1000':
            return queryset.filter(price__gte=0, price__lte=1000)
        elif self.value() == '1000-5000':
            return queryset.filter(price__gte=1000, price__lte=5000)
        elif self.value() == '5000-10000':
            return queryset.filter(price__gte=5000, price__lte=10000)
        elif self.value() == '10000+':
            return queryset.filter(price__gte=10000)
        return queryset


# Add custom filters to ProductAdmin (FIXED: Using extend instead of + with tuple)
ProductAdmin.list_filter.extend([ProductRatingFilter, ProductPriceRangeFilter])