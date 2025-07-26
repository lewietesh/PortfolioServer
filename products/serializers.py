# products/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from blog.models import Tag  # Shared with blog app
from projects.models import Technology, Project  # Shared with projects app
from .models import (
    Product, ProductGalleryImage, ProductTechnology, ProductReview, 
    ProductPurchase, ProductTag, ProductUpdate
)

User = get_user_model()


class CreatorSerializer(serializers.ModelSerializer):
    """
    Serializer for product creators
    """
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
    
    def get_full_name(self, obj):
        """Return full name or email if names not available"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.email.split('@')[0]


class BaseProjectSerializer(serializers.ModelSerializer):
    """
    Serializer for base project reference
    """
    
    class Meta:
        model = Project
        fields = ['id', 'title', 'slug', 'url']


class ProductGalleryImageSerializer(serializers.ModelSerializer):
    """
    Serializer for product gallery images
    """
    
    class Meta:
        model = ProductGalleryImage
        fields = ['id', 'image_url', 'alt_text', 'sort_order']
        read_only_fields = ['id']
    
    def validate_image_url(self, value):
        """Validate image URL format"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Image URL must be a valid HTTP/HTTPS URL.")
        return value


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for product updates/changelogs
    """
    
    class Meta:
        model = ProductUpdate
        fields = [
            'id', 'version', 'title', 'description', 
            'download_url', 'is_major', 'date_created'
        ]
        read_only_fields = ['id', 'date_created']


class ProductReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for product reviews
    """
    
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductReview
        fields = [
            'id',
            'client_name',
            'rating',
            'review_text',
            'approved',
            'date_created'
        ]
        read_only_fields = ['id', 'date_created', 'client_name']
    
    def get_client_name(self, obj):
        """Return client's display name"""
        if obj.client and (obj.client.first_name or obj.client.last_name):
            return f"{obj.client.first_name} {obj.client.last_name}".strip()
        return "Anonymous Client"
    
    def validate_rating(self, value):
        """Ensure rating is between 1 and 5"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def validate_review_text(self, value):
        """Ensure review text has minimum length if provided"""
        if value and len(value.strip()) < 20:
            raise serializers.ValidationError("Review must be at least 20 characters long.")
        return value.strip() if value else value


class ProductReviewCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating product reviews
    """
    
    class Meta:
        model = ProductReview
        fields = ['rating', 'review_text']
    
    def validate_rating(self, value):
        """Ensure rating is between 1 and 5"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def validate_review_text(self, value):
        """Ensure review text has minimum length if provided"""
        if value and len(value.strip()) < 20:
            raise serializers.ValidationError("Review must be at least 20 characters long.")
        return value.strip() if value else value


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializer for product lists
    Includes essential fields and related data
    """
    
    creator = CreatorSerializer(read_only=True)
    base_project = BaseProjectSerializer(read_only=True)
    technologies = serializers.StringRelatedField(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    gallery_images_count = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    license_display = serializers.CharField(source='get_license_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'type',
            'type_display',
            'short_description',
            'creator',
            'base_project',
            'image_url',
            'price',
            'currency',
            'demo_url',
            'featured',
            'active',
            'download_count',
            'version',
            'license_type',
            'license_display',
            'technologies',
            'tags',
            'average_rating',
            'reviews_count',
            'gallery_images_count',
            'date_created'
        ]
    
    def get_average_rating(self, obj):
        """Calculate average rating from approved reviews"""
        approved_reviews = obj.reviews.filter(approved=True)
        if approved_reviews.exists():
            total = sum(review.rating for review in approved_reviews)
            return round(total / approved_reviews.count(), 1)
        return 0
    
    def get_reviews_count(self, obj):
        """Return count of approved reviews"""
        return obj.reviews.filter(approved=True).count()
    
    def get_gallery_images_count(self, obj):
        """Return count of gallery images"""
        return obj.gallery_images.count()


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual products
    Includes full content and nested relationships
    """
    
    creator = CreatorSerializer(read_only=True)
    base_project = BaseProjectSerializer(read_only=True)
    technologies = serializers.StringRelatedField(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    gallery_images = ProductGalleryImageSerializer(many=True, read_only=True)
    updates = ProductUpdateSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    purchase_stats = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    license_display = serializers.CharField(source='get_license_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'type',
            'type_display',
            'description',
            'short_description',
            'creator',
            'base_project',
            'image_url',
            'price',
            'currency',
            'demo_url',
            'download_url',
            'repository_url',
            'documentation_url',
            'featured',
            'active',
            'download_count',
            'version',
            'license_type',
            'license_display',
            'requirements',
            'installation_notes',
            'technologies',
            'tags',
            'gallery_images',
            'updates',
            'reviews',
            'average_rating',
            'reviews_count',
            'purchase_stats',
            'date_created',
            'date_updated'
        ]
    
    def get_reviews(self, obj):
        """Get approved reviews"""
        approved_reviews = obj.reviews.filter(approved=True).order_by('-date_created')[:10]
        return ProductReviewSerializer(approved_reviews, many=True, context=self.context).data
    
    def get_average_rating(self, obj):
        """Calculate average rating from approved reviews"""
        approved_reviews = obj.reviews.filter(approved=True)
        if approved_reviews.exists():
            total = sum(review.rating for review in approved_reviews)
            return round(total / approved_reviews.count(), 1)
        return 0
    
    def get_reviews_count(self, obj):
        """Return count of approved reviews"""
        return obj.reviews.filter(approved=True).count()
    
    def get_purchase_stats(self, obj):
        """Get purchase statistics"""
        purchases = obj.purchases.filter(status='completed')
        return {
            'total_purchases': purchases.count(),
            'total_revenue': sum(p.purchase_amount for p in purchases),
            'currency': obj.currency
        }


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating products
    Handles technology and tag relationships
    """
    
    technology_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of technology IDs to associate with this product"
    )
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of tag IDs to associate with this product"
    )
    gallery_images_data = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text="List of gallery image objects"
    )
    
    # Read-only nested data
    creator = CreatorSerializer(read_only=True)
    base_project = BaseProjectSerializer(read_only=True)
    technologies = serializers.StringRelatedField(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    gallery_images = ProductGalleryImageSerializer(many=True, read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    license_display = serializers.CharField(source='get_license_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'type',
            'type_display',
            'description',
            'short_description',
            'creator',
            'base_project',
            'image_url',
            'price',
            'currency',
            'demo_url',
            'download_url',
            'repository_url',
            'documentation_url',
            'featured',
            'active',
            'version',
            'license_type',
            'license_display',
            'requirements',
            'installation_notes',
            'technology_ids',
            'tag_ids',
            'gallery_images_data',
            'technologies',
            'tags',
            'gallery_images',
            'download_count',
            'date_created',
            'date_updated'
        ]
        read_only_fields = ['id', 'creator', 'download_count', 'date_created', 'date_updated']
    
    def validate_name(self, value):
        """Ensure product name is unique and not empty"""
        if not value.strip():
            raise serializers.ValidationError("Product name cannot be empty.")
        
        # Check for uniqueness (excluding current instance during updates)
        queryset = Product.objects.filter(name__iexact=value.strip())
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A product with this name already exists.")
        
        return value.strip()
    
    def validate_short_description(self, value):
        """Validate short description"""
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError("Short description cannot exceed 500 characters.")
        return value.strip() if value else value
    
    def validate_description(self, value):
        """Validate description length"""
        if not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        if len(value.strip()) < 100:
            raise serializers.ValidationError("Description must be at least 100 characters long.")
        return value.strip()
    
    def validate_price(self, value):
        """Validate price is non-negative"""
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative.")
        return value
    
    def validate_demo_url(self, value):
        """Validate demo URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Demo URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_download_url(self, value):
        """Validate download URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Download URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_repository_url(self, value):
        """Validate repository URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Repository URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_documentation_url(self, value):
        """Validate documentation URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Documentation URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_technology_ids(self, value):
        """Validate that all technology IDs exist"""
        if value:
            existing_technologies = Technology.objects.filter(id__in=value)
            if len(existing_technologies) != len(value):
                raise serializers.ValidationError("One or more technology IDs are invalid.")
        return value
    
    def validate_tag_ids(self, value):
        """Validate that all tag IDs exist"""
        if value:
            existing_tags = Tag.objects.filter(id__in=value)
            if len(existing_tags) != len(value):
                raise serializers.ValidationError("One or more tag IDs are invalid.")
        return value
    
    def validate_type(self, value):
        """Validate product type"""
        valid_types = dict(Product.TYPE_CHOICES).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid product type. Must be one of: {list(valid_types)}")
        return value
    
    def validate_license_type(self, value):
        """Validate license type"""
        valid_licenses = dict(Product.LICENSE_CHOICES).keys()
        if value not in valid_licenses:
            raise serializers.ValidationError(f"Invalid license type. Must be one of: {list(valid_licenses)}")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Auto-generate slug if not provided
        if not data.get('slug') and data.get('name'):
            data['slug'] = slugify(data['name'])
        
        return data
    
    def create(self, validated_data):
        """Create product with technology and tag relationships"""
        technology_ids = validated_data.pop('technology_ids', [])
        tag_ids = validated_data.pop('tag_ids', [])
        gallery_images_data = validated_data.pop('gallery_images_data', [])
        
        # Set creator to current user
        validated_data['creator'] = self.context['request'].user
        
        product = Product.objects.create(**validated_data)
        
        # Associate technologies
        if technology_ids:
            for tech_id in technology_ids:
                ProductTechnology.objects.create(product=product, technology_id=tech_id)
        
        # Associate tags
        if tag_ids:
            for tag_id in tag_ids:
                ProductTag.objects.create(product=product, tag_id=tag_id)
        
        # Create gallery images
        if gallery_images_data:
            for image_data in gallery_images_data:
                ProductGalleryImage.objects.create(
                    product=product,
                    image_url=image_data['image_url'],
                    alt_text=image_data.get('alt_text', ''),
                    sort_order=image_data.get('sort_order', 0)
                )
        
        return product
    
    def update(self, instance, validated_data):
        """Update product with technology and tag relationships"""
        technology_ids = validated_data.pop('technology_ids', None)
        tag_ids = validated_data.pop('tag_ids', None)
        gallery_images_data = validated_data.pop('gallery_images_data', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update technologies if provided
        if technology_ids is not None:
            ProductTechnology.objects.filter(product=instance).delete()
            for tech_id in technology_ids:
                ProductTechnology.objects.create(product=instance, technology_id=tech_id)
        
        # Update tags if provided
        if tag_ids is not None:
            ProductTag.objects.filter(product=instance).delete()
            for tag_id in tag_ids:
                ProductTag.objects.create(product=instance, tag_id=tag_id)
        
        # Update gallery images if provided
        if gallery_images_data is not None:
            ProductGalleryImage.objects.filter(product=instance).delete()
            for image_data in gallery_images_data:
                ProductGalleryImage.objects.create(
                    product=instance,
                    image_url=image_data['image_url'],
                    alt_text=image_data.get('alt_text', ''),
                    sort_order=image_data.get('sort_order', 0)
                )
        
        return instance


class PublicProductListSerializer(serializers.ModelSerializer):
    """
    Public serializer for product lists
    Only shows active products with essential fields
    """
    
    creator_name = serializers.SerializerMethodField()
    base_project_title = serializers.SerializerMethodField()
    technologies = serializers.StringRelatedField(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    license_display = serializers.CharField(source='get_license_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'type',
            'type_display',
            'short_description',
            'creator_name',
            'base_project_title',
            'image_url',
            'price',
            'currency',
            'demo_url',
            'featured',
            'download_count',
            'version',
            'license_type',
            'license_display',
            'technologies',
            'tags',
            'average_rating',
            'reviews_count'
        ]
    
    def get_creator_name(self, obj):
        """Return creator's display name"""
        if obj.creator.first_name or obj.creator.last_name:
            return f"{obj.creator.first_name} {obj.creator.last_name}".strip()
        return obj.creator.email.split('@')[0]
    
    def get_base_project_title(self, obj):
        """Return base project title if available"""
        return obj.base_project.title if obj.base_project else None
    
    def get_average_rating(self, obj):
        """Calculate average rating from approved reviews"""
        approved_reviews = obj.reviews.filter(approved=True)
        if approved_reviews.exists():
            total = sum(review.rating for review in approved_reviews)
            return round(total / approved_reviews.count(), 1)
        return 0
    
    def get_reviews_count(self, obj):
        """Return count of approved reviews"""
        return obj.reviews.filter(approved=True).count()


class PublicProductDetailSerializer(serializers.ModelSerializer):
    """
    Public serializer for individual products
    Full product information for product pages
    """
    
    creator_name = serializers.SerializerMethodField()
    base_project = BaseProjectSerializer(read_only=True)
    technologies = serializers.StringRelatedField(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    gallery_images = ProductGalleryImageSerializer(many=True, read_only=True)
    updates = ProductUpdateSerializer(many=True, read_only=True)
    reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    license_display = serializers.CharField(source='get_license_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'type',
            'type_display',
            'description',
            'short_description',
            'creator_name',
            'base_project',
            'image_url',
            'price',
            'currency',
            'demo_url',
            'featured',
            'download_count',
            'version',
            'license_type',
            'license_display',
            'requirements',
            'installation_notes',
            'technologies',
            'tags',
            'gallery_images',
            'updates',
            'reviews',
            'average_rating',
            'reviews_count',
            'date_created'
        ]
    
    def get_creator_name(self, obj):
        """Return creator's display name"""
        if obj.creator.first_name or obj.creator.last_name:
            return f"{obj.creator.first_name} {obj.creator.last_name}".strip()
        return obj.creator.email.split('@')[0]
    
    def get_reviews(self, obj):
        """Get approved reviews"""
        approved_reviews = obj.reviews.filter(approved=True).order_by('-date_created')[:5]
        return ProductReviewSerializer(approved_reviews, many=True, context=self.context).data
    
    def get_average_rating(self, obj):
        """Calculate average rating"""
        approved_reviews = obj.reviews.filter(approved=True)
        if approved_reviews.exists():
            total = sum(review.rating for review in approved_reviews)
            return round(total / approved_reviews.count(), 1)
        return 0
    
    def get_reviews_count(self, obj):
        """Return count of approved reviews"""
        return obj.reviews.filter(approved=True).count()


class ProductPurchaseSerializer(serializers.ModelSerializer):
    """
    Serializer for product purchases
    """
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductPurchase
        fields = [
            'id',
            'product_name',
            'client_name',
            'purchase_amount',
            'currency',
            'status',
            'download_count',
            'download_limit',
            'license_key',
            'expires_at',
            'payment_method',
            'transaction_id',
            'date_created'
        ]
        read_only_fields = ['id', 'license_key', 'date_created']
    
    def get_client_name(self, obj):
        """Return client's display name"""
        if obj.client and (obj.client.first_name or obj.client.last_name):
            return f"{obj.client.first_name} {obj.client.last_name}".strip()
        return "Client"


class ProductStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for product statistics (admin use)
    """
    
    creator_name = serializers.SerializerMethodField()
    total_reviews = serializers.SerializerMethodField()
    approved_reviews = serializers.SerializerMethodField()
    pending_reviews = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_purchases = serializers.SerializerMethodField()
    total_revenue = serializers.SerializerMethodField()
    technologies_count = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'category',
            'type',
            'type_display',
            'price',
            'currency',
            'featured',
            'active',
            'download_count',
            'creator_name',
            'total_reviews',
            'approved_reviews',
            'pending_reviews',
            'average_rating',
            'total_purchases',
            'total_revenue',
            'technologies_count',
            'date_created'
        ]
    
    def get_creator_name(self, obj):
        """Get creator's name"""
        if obj.creator.first_name or obj.creator.last_name:
            return f"{obj.creator.first_name} {obj.creator.last_name}".strip()
        return obj.creator.email
    
    def get_total_reviews(self, obj):
        """Total reviews count"""
        return obj.reviews.count()
    
    def get_approved_reviews(self, obj):
        """Approved reviews count"""
        return obj.reviews.filter(approved=True).count()
    
    def get_pending_reviews(self, obj):
        """Pending reviews count"""
        return obj.reviews.filter(approved=False).count()
    
    def get_average_rating(self, obj):
        """Calculate average rating"""
        approved_reviews = obj.reviews.filter(approved=True)
        if approved_reviews.exists():
            total = sum(review.rating for review in approved_reviews)
            return round(total / approved_reviews.count(), 1)
        return 0
    
    def get_total_purchases(self, obj):
        """Total purchases count"""
        return obj.purchases.filter(status='completed').count()
    
    def get_total_revenue(self, obj):
        """Total revenue from purchases"""
        purchases = obj.purchases.filter(status='completed')
        return sum(p.purchase_amount for p in purchases)
    
    def get_technologies_count(self, obj):
        """Technologies count"""
        return obj.technologies.count()