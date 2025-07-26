# core/utils.py
from django.core.exceptions import ValidationError
from django.core.cache import cache
import re


def validate_cta_link(url):
    """
    Validate call-to-action link format
    
    Args:
        url (str): URL to validate
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If URL is invalid
    """
    if not url:
        return True
    
    # Allow relative paths, absolute URLs
    if url.startswith('/'):
        return True
    
    if url.startswith(('http://', 'https://')):
        return True
    
    # Allow mailto and tel links
    if url.startswith(('mailto:', 'tel:')):
        return True
    
    raise ValidationError("CTA link must be a valid URL, relative path, mailto, or tel link.")


def validate_social_media_structure(socials_data):
    """
    Validate social media URLs structure for AboutSection
    
    Args:
        socials_data: List of social media objects
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If validation fails
    """
    if not socials_data:
        return True
    
    if not isinstance(socials_data, list):
        raise ValidationError("Social URLs must be a list.")
    
    required_fields = ['name', 'url']
    valid_platforms = [
        'twitter', 'x', 'facebook', 'instagram', 'linkedin', 
        'github', 'youtube', 'tiktok', 'discord', 'dribbble',
        'behance', 'medium', 'dev', 'stackoverflow'
    ]
    
    for i, social in enumerate(socials_data):
        if not isinstance(social, dict):
            raise ValidationError(f"Social link {i+1} must be an object.")
        
        # Check required fields
        for field in required_fields:
            if field not in social:
                raise ValidationError(f"Social link {i+1} must have '{field}' field.")
        
        name = social['name'].lower().strip()
        url = social['url'].strip()
        
        if not name:
            raise ValidationError(f"Social link {i+1}: name cannot be empty.")
        
        if not url.startswith(('http://', 'https://')):
            raise ValidationError(f"Social link {i+1}: URL must be a valid HTTP/HTTPS URL.")
        
        # Validate URL format
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        if not url_pattern.match(url):
            raise ValidationError(f"Social link {i+1}: Invalid URL format.")
    
    return True


def get_active_hero_section():
    """
    Get the currently active hero section with caching
    
    Returns:
        HeroSection or None: Active hero section
    """
    from .models import HeroSection
    
    cache_key = 'active_hero_section'
    hero = cache.get(cache_key)
    
    if hero is None:
        try:
            hero = HeroSection.objects.get(is_active=True)
            # Cache for 15 minutes
            cache.set(cache_key, hero, 60 * 15)
        except HeroSection.DoesNotExist:
            hero = None
    
    return hero


def get_latest_about_section():
    """
    Get the latest about section with caching
    
    Returns:
        AboutSection or None: Latest about section
    """
    from .models import AboutSection
    
    cache_key = 'latest_about_section'
    about = cache.get(cache_key)
    
    if about is None:
        try:
            about = AboutSection.objects.latest('date_created')
            # Cache for 30 minutes
            cache.set(cache_key, about, 60 * 30)
        except AboutSection.DoesNotExist:
            about = None
    
    return about


def invalidate_hero_cache():
    """
    Invalidate hero section cache
    Call this when hero sections are updated
    """
    cache.delete('active_hero_section')


def invalidate_about_cache():
    """
    Invalidate about section cache
    Call this when about sections are updated
    """
    cache.delete('latest_about_section')


class CorePermissions:
    """
    Utility class for core-related permissions
    """
    
    @staticmethod
    def can_manage_hero_sections(user):
        """Check if user can manage hero sections"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_manage_about_sections(user):
        """Check if user can manage about sections"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_view_admin_content(user):
        """Check if user can view admin-only content"""
        return user.is_staff


def format_social_media_data(socials_data):
    """
    Format and clean social media data
    
    Args:
        socials_data: Raw social media data
    
    Returns:
        list: Formatted social media data
    """
    if not socials_data:
        return []
    
    formatted_socials = []
    for social in socials_data:
        formatted_social = {
            'name': social['name'].strip().lower(),
            'url': social['url'].strip(),
            'display_name': social['name'].strip().title()
        }
        
        # Add icon mapping
        icon_mapping = {
            'twitter': 'twitter',
            'x': 'twitter',  # X (formerly Twitter)
            'facebook': 'facebook',
            'instagram': 'instagram',
            'linkedin': 'linkedin',
            'github': 'github',
            'youtube': 'youtube',
            'tiktok': 'tiktok',
            'discord': 'discord',
            'dribbble': 'dribbble',
            'behance': 'behance',
            'medium': 'medium',
            'dev': 'dev',
            'stackoverflow': 'stackoverflow'
        }
        
        formatted_social['icon'] = icon_mapping.get(
            formatted_social['name'], 
            'link'  # Default icon
        )
        
        formatted_socials.append(formatted_social)
    
    return formatted_socials


def generate_core_sitemap_data():
    """
    Generate sitemap data for core pages
    
    Returns:
        list: List of core page URLs with metadata
    """
    from datetime import datetime
    
    core_pages = [
        {
            'url': '/',
            'lastmod': datetime.now(),
            'changefreq': 'weekly',
            'priority': 1.0
        },
        {
            'url': '/about/',
            'lastmod': datetime.now(),
            'changefreq': 'monthly',
            'priority': 0.9
        }
    ]
    
    return core_pages


# Constants for core app
CORE_SETTINGS = {
    'MAX_HERO_SECTIONS': 10,  # Limit total hero sections
    'MAX_ABOUT_SECTIONS': 5,  # Limit total about sections
    'HERO_CACHE_TIMEOUT': 60 * 15,  # 15 minutes
    'ABOUT_CACHE_TIMEOUT': 60 * 30,  # 30 minutes
    'MAX_SOCIAL_LINKS': 10,  # Maximum social media links
    'CTA_MAX_LENGTH': 100,  # Maximum CTA text length
    'DEFAULT_HERO_HEADING': 'Welcome to My Portfolio',
    'DEFAULT_ABOUT_TITLE': 'About Me',
}