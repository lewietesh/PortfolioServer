# projects/models.py
import uuid
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.conf import settings


class Technology(models.Model):
    """
    Master list of technologies used across projects and products
    Shared reference model
    """
    
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    icon_url = models.TextField(blank=True)
    category = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Category: frontend, backend, database, tool, etc."
    )
    
    class Meta:
        db_table = 'technology'
        verbose_name = 'Technology'
        verbose_name_plural = 'Technologies'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return self.name


class Project(models.Model):
    """
    Portfolio projects showcasing development work
    """
    
    STATUS_CHOICES = [
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('maintenance', 'Maintenance'),
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
    
    # Categorization
    category = models.CharField(max_length=100, blank=True)
    domain = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Business domain or industry"
    )
    
    # Relationships
    client = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_projects',
        limit_choices_to={'role': 'client'}
    )
    
    # Media
    image_url = models.TextField(
        blank=True,
        help_text="Main project screenshot or banner"
    )
    
    # Content fields
    description = models.TextField()
    content = models.TextField(
        blank=True,
        help_text="Detailed project content and case study"
    )
    
    # Project links
    url = models.TextField(
        blank=True,
        help_text="Live project URL"
    )
    repository_url = models.TextField(
        blank=True,
        help_text="GitHub or code repository URL"
    )
    
    # Project metrics
    likes = models.IntegerField(default=0)
    featured = models.BooleanField(default=False)
    
    # Project timeline
    completion_date = models.DateField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ongoing'
    )
    
    # Technology relationship
    technologies = models.ManyToManyField(
        Technology,
        through='ProjectTechnology',
        related_name='projects',
        blank=True
    )
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'project'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['featured']),
            models.Index(fields=['client']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from title if not provided"""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    @property
    def is_completed(self):
        """Check if project is completed"""
        return self.status == 'completed'


class ProjectGalleryImage(models.Model):
    """
    Gallery images for projects (multiple screenshots)
    """
    
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    image_url = models.TextField()
    alt_text = models.CharField(
        max_length=255, 
        blank=True,
        help_text="Alternative text for accessibility"
    )
    sort_order = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'project_gallery_image'
        verbose_name = 'Project Gallery Image'
        verbose_name_plural = 'Project Gallery Images'
        ordering = ['project', 'sort_order']
        indexes = [
            models.Index(fields=['project']),
        ]
    
    def __str__(self):
        return f"{self.project.title} - Image {self.sort_order}"


class ProjectTechnology(models.Model):
    """
    Many-to-many relationship between Project and Technology
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE
    )
    technology = models.ForeignKey(
        Technology,
        on_delete=models.CASCADE
    )
    
    class Meta:
        db_table = 'project_technology'
        unique_together = ('project', 'technology')
        verbose_name = 'Project Technology'
        verbose_name_plural = 'Project Technologies'
    
    def __str__(self):
        return f"{self.project.title} - {self.technology.name}"


class ProjectComment(models.Model):
    """
    Public comments on portfolio projects
    """
    
    # Primary fields
    id = models.CharField(
        max_length=36, 
        primary_key=True, 
        default=uuid.uuid4,
        editable=False
    )
    
    # Relationship
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    
    # Commenter information
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    
    # Comment content
    message = models.TextField()
    
    # Moderation
    approved = models.BooleanField(default=False)
    
    # Timestamp
    date_created = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'project_comment'
        verbose_name = 'Project Comment'
        verbose_name_plural = 'Project Comments'
        ordering = ['-date_created']
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['approved']),
        ]
    
    def __str__(self):
        return f"Comment by {self.name} on {self.project.title}"