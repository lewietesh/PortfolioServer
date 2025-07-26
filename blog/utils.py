# blog/utils.py
from django.utils.text import slugify
from django.core.exceptions import ValidationError
import re


def generate_unique_slug(model_class, title, instance=None):
    """
    Generate a unique slug for a model instance
    
    Args:
        model_class: The model class (e.g., BlogPost)
        title: The title to generate slug from
        instance: Current instance (for updates)
    
    Returns:
        str: Unique slug
    """
    base_slug = slugify(title)
    if not base_slug:
        base_slug = 'untitled'
    
    slug = base_slug
    counter = 1
    
    while True:
        # Check if slug exists (excluding current instance during updates)
        queryset = model_class.objects.filter(slug=slug)
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        
        if not queryset.exists():
            return slug
        
        # Generate new slug with counter
        slug = f"{base_slug}-{counter}"
        counter += 1


def estimate_reading_time(content, words_per_minute=200):
    """
    Estimate reading time for content
    
    Args:
        content (str): The content to analyze
        words_per_minute (int): Average reading speed
    
    Returns:
        int: Estimated reading time in minutes
    """
    if not content:
        return 1
    
    # Remove HTML tags and count words
    clean_content = re.sub(r'<[^>]+>', '', content)
    word_count = len(clean_content.split())
    
    # Calculate reading time (minimum 1 minute)
    return max(1, round(word_count / words_per_minute))


def validate_social_media_urls(socials_data):
    """
    Validate social media URLs structure
    
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
    
    valid_platforms = [
        'twitter', 'facebook', 'instagram', 'linkedin', 
        'github', 'youtube', 'tiktok', 'discord'
    ]
    
    for social in socials_data:
        if not isinstance(social, dict):
            raise ValidationError("Each social link must be an object.")
        
        if 'name' not in social or 'url' not in social:
            raise ValidationError("Each social link must have 'name' and 'url' fields.")
        
        name = social['name'].lower().strip()
        url = social['url'].strip()
        
        if not name:
            raise ValidationError("Social media name cannot be empty.")
        
        if not url.startswith(('http://', 'https://')):
            raise ValidationError(f"Social media URL for {name} must be a valid HTTP/HTTPS URL.")
        
        # Optional: Validate against known platforms
        if name not in valid_platforms:
            # Allow custom platforms but warn in logs
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Unknown social platform: {name}")
    
    return True


def clean_content(content):
    """
    Clean and sanitize blog content
    
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


def get_excerpt_from_content(content, max_length=200):
    """
    Generate excerpt from content if not provided
    
    Args:
        content (str): Full content
        max_length (int): Maximum excerpt length
    
    Returns:
        str: Generated excerpt
    """
    if not content:
        return ""
    
    # Remove HTML tags
    clean_content = re.sub(r'<[^>]+>', '', content)
    
    # Take first paragraph or sentences up to max_length
    sentences = clean_content.split('.')
    excerpt = ""
    
    for sentence in sentences:
        if len(excerpt + sentence) <= max_length:
            excerpt += sentence + "."
        else:
            break
    
    if not excerpt:
        # Fallback: just truncate
        excerpt = clean_content[:max_length] + "..."
    
    return excerpt.strip()


class BlogPermissions:
    """
    Utility class for blog-related permissions
    """
    
    @staticmethod
    def can_publish_post(user):
        """Check if user can publish blog posts"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_moderate_comments(user):
        """Check if user can moderate comments"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_manage_tags(user):
        """Check if user can manage tags"""
        return user.is_staff or user.role in ['admin', 'developer']
    
    @staticmethod
    def can_view_unpublished(user):
        """Check if user can view unpublished posts"""
        return user.is_staff


def get_related_posts(blog_post, limit=4):
    """
    Get related posts based on tags and category
    
    Args:
        blog_post: BlogPost instance
        limit (int): Maximum number of related posts
    
    Returns:
        QuerySet: Related blog posts
    """
    from .models import BlogPost
    
    # Get posts with similar tags, excluding current post
    related_posts = BlogPost.objects.filter(
        tags__in=blog_post.tags.all(),
        status='published'
    ).exclude(id=blog_post.id).distinct()
    
    # If not enough related posts, include posts from same category
    if related_posts.count() < limit and blog_post.category:
        category_posts = BlogPost.objects.filter(
            category=blog_post.category,
            status='published'
        ).exclude(id=blog_post.id)
        
        # Combine querysets
        from django.db.models import Q
        related_posts = BlogPost.objects.filter(
            Q(tags__in=blog_post.tags.all()) | Q(category=blog_post.category),
            status='published'
        ).exclude(id=blog_post.id).distinct()
    
    return related_posts.order_by('-date_published')[:limit]


def generate_blog_sitemap_data():
    """
    Generate data for blog sitemap
    
    Returns:
        list: List of blog post URLs with metadata
    """
    from .models import BlogPost
    
    posts = BlogPost.objects.filter(status='published').values(
        'slug', 'date_updated', 'date_published'
    )
    
    sitemap_data = []
    for post in posts:
        sitemap_data.append({
            'url': f"/blog/{post['slug']}/",
            'lastmod': post['date_updated'] or post['date_published'],
            'changefreq': 'monthly',
            'priority': 0.8
        })
    
    return sitemap_data


# Constants for blog app
BLOG_SETTINGS = {
    'DEFAULT_WORDS_PER_MINUTE': 200,
    'MAX_EXCERPT_LENGTH': 500,
    'MIN_EXCERPT_LENGTH': 50,
    'MIN_CONTENT_LENGTH': 100,
    'MAX_TAGS_PER_POST': 10,
    'DEFAULT_CACHE_TIMEOUT': 60 * 15,  # 15 minutes
    'COMMENT_MIN_LENGTH': 10,
    'COMMENT_MAX_LENGTH': 1000,
}