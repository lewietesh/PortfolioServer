# blog/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings

# For SEO mostly later in the implementation of frontend
class Tag(models.Model):
    """
    Tags for categorizing blog posts and products
    Shared across blog and products apps
    """
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7, 
        blank=True,
        help_text="Hex color code for UI display (e.g., #FF5733)"
    )
    
    class Meta:
        db_table = 'tag'
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
        ordering = ['name']
        indexes = [
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    """
    Blog posts for content publishing system
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    
    # Content fields
    excerpt = models.TextField(help_text="Short description for previews")
    content = models.TextField(help_text="Full blog post content")
    image_url = models.URLField(blank=True, help_text="Featured image URL")
    
    # Publishing fields
    date_published = models.DateField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # Relationships
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='blog_posts'
    )
    tags = models.ManyToManyField(
        Tag,
        through='BlogPostTag',
        related_name='blog_posts',
        blank=True
    )
    
    # Metrics
    view_count = models.IntegerField(default=0)
    featured = models.BooleanField(default=False)
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'blog_post'
        verbose_name = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['featured']),
            models.Index(fields=['author']),
            models.Index(fields=['date_published']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from title if not provided"""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    @property
    def is_published(self):
        """Check if the blog post is published"""
        return self.status == 'published'


class BlogPostTag(models.Model):
    """
    Many-to-many relationship between BlogPost and Tag
    """
    
    blogpost = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        db_column='blogpost_id'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        db_column='tag_id'
    )
    
    class Meta:
        db_table = 'blogpost_tag'
        unique_together = ('blogpost', 'tag')
        verbose_name = 'Blog Post Tag'
        verbose_name_plural = 'Blog Post Tags'
    
    def __str__(self):
        return f"{self.blogpost.title} - {self.tag.name}"


class BlogComment(models.Model):
    """
    Comments on blog posts with moderation system
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    blogpost = models.ForeignKey(
        BlogPost,
        on_delete=models.CASCADE,
        related_name='comments',
        db_column='blogpost_id'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        db_column='parent_id',
        help_text="Parent comment for nested replies"
    )
    
    # Commenter information
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True, help_text="Commenter's website")
    
    # Comment content
    message = models.TextField()
    
    # Moderation
    approved = models.BooleanField(default=False)
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'blog_comment'
        verbose_name = 'Blog Comment'
        verbose_name_plural = 'Blog Comments'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['blogpost']),
            models.Index(fields=['approved']),
            models.Index(fields=['parent']),
        ]
    
    def __str__(self):
        return f"Comment by {self.name} on {self.blogpost.title}"
    
    @property
    def is_reply(self):
        """Check if this comment is a reply to another comment"""
        return self.parent is not None