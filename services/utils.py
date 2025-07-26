# services/utils.py
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db.models import Count, Q, Min, Max, Avg
import re


def generate_unique_service_slug(name, instance=None):
    """
    Generate a unique slug for a service
    
    Args:
        name (str): The service name
        instance: Current service instance (for updates)
    
    Returns:
        str: Unique slug
    """
    from .models import Service
    
    base_slug = slugify(name)
    if not base_slug:
        base_slug = 'untitled-service'
    
    slug = base_slug
    counter = 1
    
    while True:
        # Check if slug exists (excluding current instance during updates)
        queryset = Service.objects.filter(slug=slug)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        
        if not queryset.exists():
            return slug
        
        # Generate new slug with counter
        slug = f"{base_slug}-{counter}"
        counter += 1


def validate_pricing_model_data(pricing_model, starting_at, pricing_tiers_data=None):
    """
    Validate pricing model consistency
    
    Args:
        pricing_model (str): The pricing model
        starting_at (float): Starting price
        pricing_tiers_data (list): Pricing tiers data
    
    Returns:
        tuple: (is_valid, errors)
    """
    errors = []
    
    # Validate pricing model and starting_at consistency
    if pricing_model == 'custom':
        # Custom pricing can have starting_at as 0
        pass
    elif pricing_model in ['fixed', 'hourly', 'per-page']:
        if starting_at <= 0:
            errors.append(f"Starting price must be greater than 0 for {pricing_model} pricing model.")
    elif pricing_model == 'tiered':
        if not pricing_tiers_data or len(pricing_tiers_data) < 2:
            errors.append("Tiered pricing requires at least 2 pricing tiers.")
        
        # Validate tier prices are in ascending order
        if pricing_tiers_data:
            prices = [tier.get('price', 0) for tier in pricing_tiers_data]
            if prices != sorted(prices):
                errors.append("Pricing tiers should be ordered from lowest to highest price.")
    
    return len(errors) == 0, errors


def validate_process_steps_data(steps_data):
    """
    Validate process steps data structure
    
    Args:
        steps_data: List of process step objects
    
    Returns:
        tuple: (is_valid, errors)
    """
    if not steps_data:
        return True, []
    
    errors = []
    required_fields = ['title', 'description', 'step_number']
    step_numbers = []
    
    for i, step_data in enumerate(steps_data):
        # Check required fields
        for field in required_fields:
            if field not in step_data or not step_data[field]:
                errors.append(f"Process step {i+1} must have '{field}' field.")
        
        # Validate step_number
        step_number = step_data.get('step_number')
        if step_number:
            if not isinstance(step_number, int) or step_number <= 0:
                errors.append(f"Process step {i+1} step_number must be a positive integer.")
            elif step_number in step_numbers:
                errors.append(f"Process step {i+1} step_number {step_number} is duplicated.")
            else:
                step_numbers.append(step_number)
    
    # Check for sequential step numbers
    if step_numbers and sorted(step_numbers) != list(range(1, len(step_numbers) + 1)):
        errors.append("Process step numbers should be sequential starting from 1.")
    
    return len(errors) == 0, errors


def validate_faqs_data(faqs_data):
    """
    Validate FAQs data structure
    
    Args:
        faqs_data: List of FAQ objects
    
    Returns:
        tuple: (is_valid, errors)
    """
    if not faqs_data:
        return True, []
    
    errors = []
    required_fields = ['question', 'answer']
    
    for i, faq_data in enumerate(faqs_data):
        # Check required fields
        for field in required_fields:
            if field not in faq_data or not faq_data[field].strip():
                errors.append(f"FAQ {i+1} must have '{field}' field.")
        
        # Validate answer length
        answer = faq_data.get('answer', '')
        if answer and len(answer.strip()) < 20:
            errors.append(f"FAQ {i+1} answer must be at least 20 characters long.")
        
        # Validate sort_order if provided
        sort_order = faq_data.get('sort_order', 0)
        if not isinstance(sort_order, int) or sort_order < 0:
            errors.append(f"FAQ {i+1} sort_order must be a non-negative integer.")
    
    return len(errors) == 0, errors


def get_featured_services(limit=6):
    """
    Get featured services with caching
    
    Args:
        limit (int): Maximum number of services to return
    
    Returns:
        QuerySet: Featured services
    """
    from .models import Service
    
    cache_key = f'featured_services_{limit}'
    services = cache.get(cache_key)
    
    if services is None:
        services = Service.objects.filter(
            featured=True,
            active=True
        ).prefetch_related('pricing_tiers')[:limit]
        
        # Cache for 30 minutes
        cache.set(cache_key, services, 60 * 30)
    
    return services


def get_services_by_category(category, limit=None):
    """
    Get services by category with caching
    
    Args:
        category (str): Service category
        limit (int): Maximum number of services
    
    Returns:
        QuerySet: Services in the category
    """
    from .models import Service
    
    cache_key = f'services_category_{category}_{limit or "all"}'
    services = cache.get(cache_key)
    
    if services is None:
        services = Service.objects.filter(
            category__iexact=category,
            active=True
        ).prefetch_related('pricing_tiers')
        
        if limit:
            services = services[:limit]
        
        # Cache for 20 minutes
        cache.set(cache_key, services, 60 * 20)
    
    return services


def get_service_categories_with_counts():
    """
    Get all service categories with service counts
    
    Returns:
        dict: Categories with statistics
    """
    from .models import Service
    
    cache_key = 'service_categories_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        categories = Service.objects.filter(active=True).values('category').annotate(
            count=Count('id'),
            avg_price=Avg('starting_at'),
            min_price=Min('starting_at'),
            max_price=Max('starting_at')
        ).order_by('category')
        
        stats = {
            'categories': list(categories),
            'total_categories': len(categories),
            'total_services': Service.objects.filter(active=True).count()
        }
        
        # Cache for 1 hour
        cache.set(cache_key, stats, 60 * 60)
    
    return stats


def get_pricing_models_stats():
    """
    Get pricing models statistics
    
    Returns:
        dict: Pricing models with statistics
    """
    from .models import Service
    
    cache_key = 'pricing_models_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        pricing_models = Service.objects.filter(active=True).values('pricing_model').annotate(
            count=Count('id'),
            avg_price=Avg('starting_at'),
            min_price=Min('starting_at'),
            max_price=Max('starting_at')
        ).order_by('pricing_model')
        
        stats = {
            'pricing_models': list(pricing_models),
            'total_models': len(pricing_models)
        }
        
        # Cache for 1 hour
        cache.set(cache_key, stats, 60 * 60)
    
    return stats


def get_service_statistics():
    """
    Generate comprehensive service statistics
    
    Returns:
        dict: Service statistics
    """
    from .models import Service, ServicePricingTier
    
    cache_key = 'service_statistics'
    stats = cache.get(cache_key)
    
    if stats is None:
        total_services = Service.objects.count()
        active_services = Service.objects.filter(active=True).count()
        featured_services = Service.objects.filter(featured=True, active=True).count()
        
        # Pricing statistics
        pricing_stats = Service.objects.filter(active=True).aggregate(
            min_price=Min('starting_at'),
            max_price=Max('starting_at'),
            avg_price=Avg('starting_at')
        )
        
        # Category distribution
        category_distribution = Service.objects.filter(active=True).values('category').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Pricing model distribution
        pricing_model_distribution = Service.objects.filter(active=True).values('pricing_model').annotate(
            count=Count('id')
        ).order_by('-count')
        
        stats = {
            'total_services': total_services,
            'active_services': active_services,
            'featured_services': featured_services,
            'activation_rate': round((active_services / total_services * 100), 2) if total_services > 0 else 0,
            'pricing_stats': pricing_stats,
            'popular_categories': list(category_distribution),
            'pricing_model_distribution': list(pricing_model_distribution)
        }
        
        # Cache for 2 hours
        cache.set(cache_key, stats, 60 * 120)
    
    return stats


def invalidate_service_caches():
    """
    Invalidate all service-related caches
    Call this when services are updated
    """
    cache_keys = [
        'featured_services_6',
        'featured_services_4',
        'service_categories_stats',
        'pricing_models_stats',
        'service_statistics'
    ]
    cache.delete_many(cache_keys)
    
    # Also clear category-specific caches (we'll use a pattern)
    from django.core.cache.utils import make_template_fragment_key
    from .models import Service
    
    categories = Service.objects.values_list('category', flat=True).distinct()
    for category in categories:
        cache.delete(f'services_category_{category}_all')
        cache.delete(f'services_category_{category}_None')


class ServicePermissions:
    """
    Utility class for service-related permissions
    """
    
    @staticmethod
    def can_manage_services(user):
        """Check if user can manage services"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_manage_pricing(user):
        """Check if user can manage pricing tiers"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_view_all_services(user):
        """Check if user can view all services (including inactive)"""
        return user.is_staff
    
    @staticmethod
    def can_feature_services(user):
        """Check if user can feature/unfeature services"""
        return user.is_staff or user.role in ['admin', 'developer']


def calculate_service_price_estimate(service, requirements=None):
    """
    Calculate estimated price for a service based on requirements
    
    Args:
        service: Service instance
        requirements (dict): Client requirements
    
    Returns:
        dict: Price estimation
    """
    base_price = service.starting_at
    
    if service.pricing_model == 'fixed':
        return {
            'estimated_price': base_price,
            'currency': service.currency,
            'pricing_model': service.pricing_model,
            'breakdown': 'Fixed price service'
        }
    
    elif service.pricing_model == 'hourly':
        estimated_hours = requirements.get('estimated_hours', 10) if requirements else 10
        total_price = base_price * estimated_hours
        
        return {
            'estimated_price': total_price,
            'currency': service.currency,
            'pricing_model': service.pricing_model,
            'breakdown': f'{estimated_hours} hours × {service.currency}{base_price}/hour'
        }
    
    elif service.pricing_model == 'per-page':
        page_count = requirements.get('page_count', 5) if requirements else 5
        total_price = base_price * page_count
        
        return {
            'estimated_price': total_price,
            'currency': service.currency,
            'pricing_model': service.pricing_model,
            'breakdown': f'{page_count} pages × {service.currency}{base_price}/page'
        }
    
    elif service.pricing_model == 'tiered':
        # Return pricing tier options
        tiers = service.pricing_tiers.all().order_by('price')
        return {
            'pricing_tiers': [
                {
                    'name': tier.name,
                    'price': tier.price,
                    'currency': tier.currency,
                    'recommended': tier.recommended
                }
                for tier in tiers
            ],
            'pricing_model': service.pricing_model
        }
    
    else:  # custom
        return {
            'pricing_model': service.pricing_model,
            'message': 'Contact us for custom pricing based on your specific requirements.'
        }


def generate_service_sitemap_data():
    """
    Generate data for service sitemap
    
    Returns:
        list: List of service URLs with metadata
    """
    from .models import Service
    
    services = Service.objects.filter(active=True).values(
        'slug', 'date_updated', 'date_created'
    )
    
    sitemap_data = []
    for service in services:
        sitemap_data.append({
            'url': f"/services/{service['slug']}/",
            'lastmod': service['date_updated'],
            'changefreq': 'weekly',
            'priority': 0.8
        })
    
    return sitemap_data


def clean_service_content(content):
    """
    Clean and sanitize service content
    
    Args:
        content (str): Raw content
    
    Returns:
        str: Cleaned content
    """
    if not content:
        return content
    
    # Remove extra whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    # Remove potentially harmful scripts (basic sanitization)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    
    return content


# Constants for services app
SERVICE_SETTINGS = {
    'MAX_PRICING_TIERS': 5,
    'MAX_PROCESS_STEPS': 10,
    'MAX_DELIVERABLES': 15,
    'MAX_TOOLS': 20,
    'MAX_USECASES': 10,
    'MAX_FAQS': 20,
    'FEATURED_SERVICES_CACHE_TIMEOUT': 60 * 30,  # 30 minutes
    'CATEGORY_CACHE_TIMEOUT': 60 * 20,           # 20 minutes
    'STATS_CACHE_TIMEOUT': 60 * 120,             # 2 hours
    'DEFAULT_FEATURED_LIMIT': 6,
    'MIN_DESCRIPTION_LENGTH': 100,
    'MIN_FAQ_ANSWER_LENGTH': 20,
    'SUPPORTED_CURRENCIES': ['USD', 'EUR', 'GBP', 'KES'],
    'DEFAULT_CURRENCY': 'USD',
}


def validate_currency(currency):
    """
    Validate currency code
    
    Args:
        currency (str): Currency code
    
    Returns:
        bool: True if valid
    """
    return currency.upper() in SERVICE_SETTINGS['SUPPORTED_CURRENCIES']


def format_price_display(price, currency):
    """
    Format price for display
    
    Args:
        price (float): Price amount
        currency (str): Currency code
    
    Returns:
        str: Formatted price string
    """
    currency_symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'KES': 'KSh'
    }
    
    symbol = currency_symbols.get(currency.upper(), currency.upper())
    
    if price >= 1000:
        return f"{symbol}{price:,.0f}"
    else:
        return f"{symbol}{price:.2f}".rstrip('0').rstrip('.')


def get_recommended_services_for_budget(budget, currency='USD'):
    """
    Get services that fit within a specific budget
    
    Args:
        budget (float): Client budget
        currency (str): Currency code
    
    Returns:
        QuerySet: Services within budget
    """
    from .models import Service
    
    return Service.objects.filter(
        active=True,
        starting_at__lte=budget,
        currency=currency
    ).order_by('starting_at')