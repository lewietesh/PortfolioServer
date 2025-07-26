# products/utils.py
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import Count, Q, Avg, Sum
import re
import uuid
import string
import random


def generate_unique_product_slug(name, instance=None):
    """
    Generate a unique slug for a product
    
    Args:
        name (str): The product name
        instance: Current product instance (for updates)
    
    Returns:
        str: Unique slug
    """
    from .models import Product
    
    base_slug = slugify(name)
    if not base_slug:
        base_slug = 'untitled-product'
    
    slug = base_slug
    counter = 1
    
    while True:
        # Check if slug exists (excluding current instance during updates)
        queryset = Product.objects.filter(slug=slug)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        
        if not queryset.exists():
            return slug
        
        # Generate new slug with counter
        slug = f"{base_slug}-{counter}"
        counter += 1


def generate_license_key():
    """
    Generate a unique license key for product purchases
    
    Returns:
        str: Unique license key
    """
    # Generate a random license key (format: XXXX-XXXX-XXXX-XXXX)
    segments = []
    for _ in range(4):
        segment = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        segments.append(segment)
    
    return '-'.join(segments)


def validate_product_urls(demo_url, download_url, repository_url, documentation_url):
    """
    Validate product URLs
    
    Args:
        demo_url (str): Demo URL
        download_url (str): Download URL
        repository_url (str): Repository URL
        documentation_url (str): Documentation URL
    
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    
    # URL pattern for validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    # Validate URLs
    urls_to_check = [
        ('Demo URL', demo_url),
        ('Download URL', download_url),
        ('Repository URL', repository_url),
        ('Documentation URL', documentation_url)
    ]
    
    for url_name, url in urls_to_check:
        if url and not url_pattern.match(url):
            errors.append(f"{url_name} format is invalid.")
    
    # Special validation for repository URL
    if repository_url:
        valid_repo_domains = [
            'github.com', 'gitlab.com', 'bitbucket.org', 
            'sourceforge.net', 'codeberg.org'
        ]
        
        is_valid_repo = any(domain in repository_url.lower() for domain in valid_repo_domains)
        if not is_valid_repo:
            # Log warning but don't fail validation
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Repository URL may not be from a known platform: {repository_url}")
    
    return len(errors) == 0, errors


def calculate_product_rating(product):
    """
    Calculate average rating for a product
    
    Args:
        product: Product instance
    
    Returns:
        dict: Rating statistics
    """
    approved_reviews = product.reviews.filter(approved=True)
    
    if not approved_reviews.exists():
        return {
            'average_rating': 0,
            'total_reviews': 0,
            'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        }
    
    # Calculate average
    total_rating = sum(review.rating for review in approved_reviews)
    average_rating = round(total_rating / approved_reviews.count(), 1)
    
    # Calculate distribution
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for review in approved_reviews:
        rating_distribution[review.rating] += 1
    
    return {
        'average_rating': average_rating,
        'total_reviews': approved_reviews.count(),
        'rating_distribution': rating_distribution
    }


def get_featured_products(limit=6):
    """
    Get featured products with caching
    
    Args:
        limit (int): Maximum number of products to return
    
    Returns:
        QuerySet: Featured products
    """
    from .models import Product
    
    cache_key = f'featured_products_{limit}'
    products = cache.get(cache_key)
    
    if products is None:
        products = Product.objects.filter(
            featured=True,
            active=True
        ).select_related('creator', 'base_project').prefetch_related('technologies', 'tags')[:limit]
        
        # Cache for 30 minutes
        cache.set(cache_key, products, 60 * 30)
    
    return products


def get_recent_products(limit=4):
    """
    Get recent products with caching
    
    Args:
        limit (int): Maximum number of products to return
    
    Returns:
        QuerySet: Recent products
    """
    from .models import Product
    
    cache_key = f'recent_products_{limit}'
    products = cache.get(cache_key)
    
    if products is None:
        products = Product.objects.filter(
            active=True
        ).select_related('creator', 'base_project').prefetch_related('technologies', 'tags').order_by('-date_created')[:limit]
        
        # Cache for 15 minutes
        cache.set(cache_key, products, 60 * 15)
    
    return products


def get_top_rated_products(limit=6, min_reviews=3):
    """
    Get top-rated products
    
    Args:
        limit (int): Maximum number of products
        min_reviews (int): Minimum number of reviews required
    
    Returns:
        QuerySet: Top-rated products
    """
    from .models import Product
    
    cache_key = f'top_rated_products_{limit}_{min_reviews}'
    products = cache.get(cache_key)
    
    if products is None:
        products = Product.objects.filter(active=True).annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__approved=True)),
            reviews_count=Count('reviews', filter=Q(reviews__approved=True))
        ).filter(
            reviews_count__gte=min_reviews
        ).order_by('-avg_rating')[:limit]
        
        # Cache for 1 hour
        cache.set(cache_key, products, 60 * 60)
    
    return products


def get_bestselling_products(limit=6):
    """
    Get best-selling products
    
    Args:
        limit (int): Maximum number of products
    
    Returns:
        QuerySet: Best-selling products
    """
    from .models import Product
    
    cache_key = f'bestselling_products_{limit}'
    products = cache.get(cache_key)
    
    if products is None:
        products = Product.objects.filter(active=True).annotate(
            purchase_count=Count('purchases', filter=Q(purchases__status='completed'))
        ).filter(
            purchase_count__gt=0
        ).order_by('-purchase_count')[:limit]
        
        # Cache for 1 hour
        cache.set(cache_key, products, 60 * 60)
    
    return products


def get_product_statistics():
    """
    Generate comprehensive product statistics
    
    Returns:
        dict: Product statistics
    """
    from .models import Product, ProductReview, ProductPurchase
    
    cache_key = 'product_statistics'
    stats = cache.get(cache_key)
    
    if stats is None:
        total_products = Product.objects.count()
        active_products = Product.objects.filter(active=True).count()
        featured_products = Product.objects.filter(featured=True, active=True).count()
        free_products = Product.objects.filter(price=0, active=True).count()
        
        # Review statistics
        total_reviews = ProductReview.objects.count()
        approved_reviews = ProductReview.objects.filter(approved=True).count()
        pending_reviews = ProductReview.objects.filter(approved=False).count()
        
        # Purchase statistics
        total_purchases = ProductPurchase.objects.filter(status='completed').count()
        total_revenue = ProductPurchase.objects.filter(status='completed').aggregate(
            total=Sum('purchase_amount')
        )['total'] or 0
        
        # Download statistics
        total_downloads = Product.objects.aggregate(total=Sum('download_count'))['total'] or 0
        
        # Category distribution
        category_distribution = Product.objects.filter(active=True).values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Type distribution
        type_distribution = Product.objects.filter(active=True).values('type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        stats = {
            'total_products': total_products,
            'active_products': active_products,
            'featured_products': featured_products,
            'free_products': free_products,
            'paid_products': active_products - free_products,
            'activation_rate': round((active_products / total_products * 100), 2) if total_products > 0 else 0,
            'total_reviews': total_reviews,
            'approved_reviews': approved_reviews,
            'pending_reviews': pending_reviews,
            'review_approval_rate': round((approved_reviews / total_reviews * 100), 2) if total_reviews > 0 else 0,
            'total_purchases': total_purchases,
            'total_revenue': float(total_revenue),
            'total_downloads': total_downloads,
            'popular_categories': list(category_distribution),
            'type_distribution': list(type_distribution)
        }
        
        # Cache for 2 hours
        cache.set(cache_key, stats, 60 * 120)
    
    return stats


def invalidate_product_caches():
    """
    Invalidate all product-related caches
    Call this when products are updated
    """
    cache_keys = [
        'featured_products_6',
        'featured_products_4',
        'recent_products_4',
        'recent_products_6',
        'top_rated_products_6_3',
        'bestselling_products_6',
        'product_statistics'
    ]
    cache.delete_many(cache_keys)


class ProductPermissions:
    """
    Utility class for product-related permissions
    """
    
    @staticmethod
    def can_manage_products(user):
        """Check if user can manage products"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_moderate_reviews(user):
        """Check if user can moderate product reviews"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_view_all_products(user):
        """Check if user can view all products (including inactive)"""
        return user.is_staff
    
    @staticmethod
    def can_download_product(user, product):
        """Check if user can download a product"""
        # Free products can be downloaded by anyone
        if product.price == 0:
            return True
        
        # Paid products require authentication and purchase
        if not user.is_authenticated:
            return False
        
        # Check if user has purchased the product
        from .models import ProductPurchase
        return ProductPurchase.objects.filter(
            product=product,
            client=user,
            status='completed'
        ).exists()
    
    @staticmethod
    def can_review_product(user, product):
        """Check if user can review a product"""
        if not product.active:
            return False
        
        # Only clients can review products
        if not user.is_authenticated or user.role != 'client':
            return False
        
        # Check if user has already reviewed this product
        from .models import ProductReview
        existing_review = ProductReview.objects.filter(
            product=product,
            client=user
        ).exists()
        return not existing_review


def get_related_products(product, limit=4):
    """
    Get related products based on technologies, tags, and category
    
    Args:
        product: Product instance
        limit (int): Maximum number of related products
    
    Returns:
        QuerySet: Related products
    """
    from .models import Product
    
    # Get products with similar technologies, tags, or category
    related_products = Product.objects.filter(
        Q(technologies__in=product.technologies.all()) | 
        Q(tags__in=product.tags.all()) |
        Q(category=product.category),
        active=True
    ).exclude(id=product.id).distinct()
    
    # Order by relevance (products with more matching attributes first)
    related_products = related_products.annotate(
        matching_tech_count=Count('technologies', filter=Q(technologies__in=product.technologies.all())),
        matching_tag_count=Count('tags', filter=Q(tags__in=product.tags.all()))
    ).order_by('-matching_tech_count', '-matching_tag_count', '-date_created')
    
    return related_products[:limit]


def validate_gallery_images_data(images_data):
    """
    Validate gallery images data structure
    
    Args:
        images_data: List of image objects
    
    Returns:
        tuple: (is_valid, errors)
    """
    if not images_data:
        return True, []
    
    errors = []
    
    if not isinstance(images_data, list):
        return False, ["Gallery images must be a list."]
    
    if len(images_data) > 10:  # Limit gallery size
        errors.append("Maximum 10 gallery images allowed per product.")
    
    for i, image_data in enumerate(images_data):
        if not isinstance(image_data, dict):
            errors.append(f"Gallery image {i+1} must be an object.")
            continue
        
        # Required fields
        if 'image_url' not in image_data:
            errors.append(f"Gallery image {i+1} must have 'image_url' field.")
            continue
        
        # Validate URL format
        if not image_data['image_url'].startswith(('http://', 'https://')):
            errors.append(f"Gallery image {i+1} URL must be a valid HTTP/HTTPS URL.")
        
        # Validate sort_order if provided
        sort_order = image_data.get('sort_order', 0)
        if not isinstance(sort_order, int) or sort_order < 0:
            errors.append(f"Gallery image {i+1} sort_order must be a non-negative integer.")
        
        # Validate alt_text length if provided
        alt_text = image_data.get('alt_text', '')
        if alt_text and len(alt_text) > 255:
            errors.append(f"Gallery image {i+1} alt_text cannot exceed 255 characters.")
    
    return len(errors) == 0, errors


def format_price_display(price, currency):
    """
    Format price for display
    
    Args:
        price (float): Price amount
        currency (str): Currency code
    
    Returns:
        str: Formatted price string
    """
    if price == 0:
        return "FREE"
    
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'KSH': 'KSh'
    }
    
    symbol = currency_symbols.get(currency.upper(), currency.upper())
    
    if price >= 1000:
        return f"{symbol}{price:,.0f}"
    else:
        return f"{symbol}{price:.2f}".rstrip('0').rstrip('.')


def calculate_product_revenue(product):
    """
    Calculate total revenue for a product
    
    Args:
        product: Product instance
    
    Returns:
        dict: Revenue statistics
    """
    completed_purchases = product.purchases.filter(status='completed')
    
    total_revenue = sum(p.purchase_amount for p in completed_purchases)
    total_purchases = completed_purchases.count()
    
    return {
        'total_revenue': float(total_revenue),
        'total_purchases': total_purchases,
        'average_purchase_amount': float(total_revenue / total_purchases) if total_purchases > 0 else 0,
        'currency': product.currency
    }


def get_product_categories_with_counts():
    """
    Get all product categories with counts and statistics
    
    Returns:
        dict: Categories with statistics
    """
    from .models import Product
    
    cache_key = 'product_categories_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        categories = Product.objects.filter(active=True).values('category').annotate(
            count=Count('id'),
            avg_price=Avg('price'),
            free_count=Count('id', filter=Q(price=0)),
            paid_count=Count('id', filter=Q(price__gt=0))
        ).order_by('category')
        
        stats = {
            'categories': list(categories),
            'total_categories': len(categories),
            'total_products': Product.objects.filter(active=True).count()
        }
        
        # Cache for 1 hour
        cache.set(cache_key, stats, 60 * 60)
    
    return stats


def get_product_types_with_counts():
    """
    Get all product types with counts and statistics
    
    Returns:
        dict: Types with statistics
    """
    from .models import Product
    
    cache_key = 'product_types_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        types = Product.objects.filter(active=True).values('type').annotate(
            count=Count('id'),
            avg_price=Avg('price'),
            free_count=Count('id', filter=Q(price=0)),
            paid_count=Count('id', filter=Q(price__gt=0))
        ).order_by('type')
        
        stats = {
            'types': list(types),
            'total_types': len(types)
        }
        
        # Cache for 1 hour
        cache.set(cache_key, stats, 60 * 60)
    
    return stats


# Constants for products app
PRODUCT_SETTINGS = {
    'MAX_GALLERY_IMAGES': 10,
    'MAX_TECHNOLOGIES_PER_PRODUCT': 15,
    'MAX_TAGS_PER_PRODUCT': 10,
    'FEATURED_PRODUCTS_CACHE_TIMEOUT': 60 * 30,  # 30 minutes
    'RECENT_PRODUCTS_CACHE_TIMEOUT': 60 * 15,    # 15 minutes
    'STATS_CACHE_TIMEOUT': 60 * 120,             # 2 hours
    'DEFAULT_FEATURED_LIMIT': 6,
    'DEFAULT_RECENT_LIMIT': 4,
    'DEFAULT_RELATED_LIMIT': 4,
    'MIN_REVIEWS_FOR_TOP_RATED': 3,
    'REVIEW_MIN_LENGTH': 20,
    'REVIEW_MAX_LENGTH': 1000,
    'PRODUCT_DESCRIPTION_MIN_LENGTH': 100,
    'SHORT_DESCRIPTION_MIN_LENGTH': 50,
    'SUPPORTED_CURRENCIES': ['USD', 'EUR', 'GBP', 'KSH'],
    'DEFAULT_CURRENCY': 'KSH',
    'SUPPORTED_LICENSE_TYPES': [
        'single_use', 'multi_use', 'unlimited', 'open_source'
    ],
    'SUPPORTED_PRODUCT_TYPES': [
        'website_template', 'web_app', 'component', 'theme', 'plugin', 'tool'
    ],
}


def validate_license_type(license_type):
    """
    Validate license type
    
    Args:
        license_type (str): License type
    
    Returns:
        bool: True if valid
    """
    return license_type in PRODUCT_SETTINGS['SUPPORTED_LICENSE_TYPES']


def validate_product_type(product_type):
    """
    Validate product type
    
    Args:
        product_type (str): Product type
    
    Returns:
        bool: True if valid
    """
    return product_type in PRODUCT_SETTINGS['SUPPORTED_PRODUCT_TYPES']