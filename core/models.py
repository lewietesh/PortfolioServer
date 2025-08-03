# core/models.py
from django.db import models
from django.utils import timezone


class HeroSection(models.Model):
    """
    Hero section content for different pages
    Each route can have its own hero section
    """
    
    id = models.AutoField(primary_key=True)
    heading = models.CharField(max_length=255)
    subheading = models.CharField(max_length=500, blank=True)
    cta_text = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Call-to-action button text"
    )
    cta_link = models.TextField(
        blank=True,
        help_text="Call-to-action button URL"
    )
    route_name = models.CharField(
        max_length=100,
        default='home',
        help_text="Route name for this hero section (e.g., 'home', 'projects', 'about')"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one hero section should be active per route"
    )
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'hero_section'
        verbose_name = 'Hero Section'
        verbose_name_plural = 'Hero Sections'
        ordering = ['-date_created']
        unique_together = ('route_name', 'is_active')  # Ensure only one active hero per route
    
    def __str__(self):
        return f"{self.heading} ({self.route_name})"
    
    def save(self, *args, **kwargs):
        """Ensure only one active hero section exists per route"""
        if self.is_active:
            HeroSection.objects.filter(
                route_name=self.route_name, 
                is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class AboutSection(models.Model):
    """
    About section content for about page
    Should only have one active record at a time
    """
    
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    media_url = models.TextField(
        blank=True,
        help_text="URL for profile image or video"
    )
    socials_urls = models.JSONField(
        blank=True,
        null=True,
        help_text="JSON array of social media links: [{'name': 'twitter', 'url': '...'}]"
    )
    
    # Timestamps
    date_created = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'about_section'
        verbose_name = 'About Section'
        verbose_name_plural = 'About Sections'
        ordering = ['-date_created']
    
    def __str__(self):
        return self.title