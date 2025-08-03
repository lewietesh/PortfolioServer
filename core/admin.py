# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import HeroSection, AboutSection


@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    """
    Admin interface for HeroSection model
    """
    
    list_display = [
        'heading', 
        'route_name',
        'subheading_preview', 
        'is_active_display', 
        'has_cta',
        'date_created',
        'date_updated'
    ]
    list_filter = ['is_active', 'route_name', 'date_created']
    search_fields = ['heading', 'subheading', 'route_name']
    readonly_fields = ['date_created', 'date_updated']
    
    fieldsets = (
        ('Content', {
            'fields': ('heading', 'subheading', 'route_name')
        }),
        ('Call to Action', {
            'fields': ('cta_text', 'cta_link'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def subheading_preview(self, obj):
        """Show truncated subheading in list view"""
        if obj.subheading:
            return (obj.subheading[:50] + '...') if len(obj.subheading) > 50 else obj.subheading
        return '-'
    subheading_preview.short_description = 'Subheading Preview'
    
    def is_active_display(self, obj):
        """Display active status with color coding"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>'
            )
        return format_html(
            '<span style="color: red;">✗ Inactive</span>'
        )
    is_active_display.short_description = 'Status'
    
    def has_cta(self, obj):
        """Check if hero section has call-to-action"""
        return bool(obj.cta_text and obj.cta_link)
    has_cta.boolean = True
    has_cta.short_description = 'Has CTA'
    
    actions = ['activate_hero', 'deactivate_hero']
    
    def activate_hero(self, request, queryset):
        """Custom action to activate selected hero (deactivates others in same route)"""
        if queryset.count() > 1:
            self.message_user(
                request, 
                "You can only activate one hero section at a time.", 
                level='error'
            )
            return
        
        hero = queryset.first()
        # Deactivate others in the same route
        HeroSection.objects.filter(route_name=hero.route_name).update(is_active=False)
        # Activate selected
        queryset.update(is_active=True)
        
        self.message_user(
            request, 
            f"Successfully activated hero section: {hero.heading} for route: {hero.route_name}"
        )
    activate_hero.short_description = "Activate selected hero section"
    
    def deactivate_hero(self, request, queryset):
        """Custom action to deactivate selected heroes"""
        count = queryset.update(is_active=False)
        self.message_user(
            request, 
            f"Successfully deactivated {count} hero section(s)."
        )
    deactivate_hero.short_description = "Deactivate selected hero sections"
    
    def save_model(self, request, obj, form, change):
        """Override save to handle business logic"""
        # If setting this as active, deactivate others in the same route
        if obj.is_active:
            HeroSection.objects.filter(route_name=obj.route_name).exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    """
    Admin interface for AboutSection model
    """
    
    list_display = [
        'title', 
        'description_preview',
        'has_media',
        'social_links_count',
        'date_created',
        'date_updated'
    ]
    list_filter = ['date_created']
    search_fields = ['title', 'description']
    readonly_fields = ['date_created', 'date_updated', 'preview_socials']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description')
        }),
        ('Media', {
            'fields': ('media_url',),
            'classes': ('collapse',)
        }),
        ('Social Media Links', {
            'fields': ('socials_urls', 'preview_socials'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def description_preview(self, obj):
        """Show truncated description in list view"""
        if obj.description:
            return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
        return '-'
    description_preview.short_description = 'Description Preview'
    
    def has_media(self, obj):
        """Check if about section has media URL"""
        return bool(obj.media_url)
    has_media.boolean = True
    has_media.short_description = 'Has Media'
    
    def social_links_count(self, obj):
        """Count of social media links"""
        if obj.socials_urls:
            return len(obj.socials_urls)
        return 0
    social_links_count.short_description = 'Social Links'
    
    def preview_socials(self, obj):
        """Preview social media links in admin"""
        if not obj.socials_urls:
            return "No social links configured"
        
        links_html = []
        for social in obj.socials_urls:
            name = social.get('name', 'Unknown')
            url = social.get('url', '#')
            links_html.append(
                f'<a href="{url}" target="_blank" style="margin-right: 10px; '
                f'display: inline-block; padding: 2px 6px; background: #f0f0f0; '
                f'border-radius: 3px; text-decoration: none; color: #333;">{name}</a>'
            )
        
        return mark_safe(''.join(links_html))
    preview_socials.short_description = 'Social Media Preview'
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).order_by('-date_created')


# Admin site customization
admin.site.site_header = "Portfolio API Administration"
admin.site.site_title = "Portfolio Admin"
admin.site.index_title = "Welcome to Portfolio Administration"