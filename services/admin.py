# services/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Avg
from .models import (
    Service, ServicePricingTier, ServiceFeature, PricingTierFeature,
    ServiceProcessStep, ServiceDeliverable, ServiceTool, 
    ServicePopularUseCase, ServiceFAQ
)


@admin.register(ServiceFeature)
class ServiceFeatureAdmin(admin.ModelAdmin):
    """
    Admin interface for ServiceFeature model
    """
    
    # FIXED: Changed 'name' to 'title' to match model field
    list_display = ['title', 'description_preview', 'icon_display', 'id']
    search_fields = ['title', 'description']  # Changed 'name' to 'title'
    
    def description_preview(self, obj):
        """Show truncated description"""
        if obj.description:
            return (obj.description[:50] + '...') if len(obj.description) > 50 else obj.description
        return '-'
    description_preview.short_description = 'Description Preview'
    
    def icon_display(self, obj):
        """Display feature icon if available"""
        # FIXED: Changed 'icon_url' to 'icon_class' to match model field
        if obj.icon_class:
            return format_html(
                '<i class="{}" style="font-size: 20px;"></i> {}',
                obj.icon_class, obj.icon_class
            )
        return '-'
    icon_display.short_description = 'Icon'


class ServicePricingTierInline(admin.TabularInline):
    """
    Inline admin for service pricing tiers
    """
    model = ServicePricingTier
    extra = 1
    fields = ['name', 'price', 'currency', 'unit', 'estimated_delivery', 'recommended', 'sort_order']
    ordering = ['sort_order']


class ServiceProcessStepInline(admin.TabularInline):
    """
    Inline admin for service process steps
    """
    model = ServiceProcessStep
    extra = 1
    # FIXED: Changed 'step_number' to 'step_order' to match model field
    fields = ['step_order', 'title', 'description']
    ordering = ['step_order']


class ServiceDeliverableInline(admin.TabularInline):
    """
    Inline admin for service deliverables
    """
    model = ServiceDeliverable
    extra = 1
    # FIXED: Changed 'name' to 'description' to match model field
    fields = ['description', 'icon_class', 'sort_order']


class ServiceToolInline(admin.TabularInline):
    """
    Inline admin for service tools
    """
    model = ServiceTool
    extra = 1
    # FIXED: Changed field names to match model
    fields = ['tool_name', 'tool_url', 'icon_url']


class ServicePopularUsecaseInline(admin.TabularInline):
    """
    Inline admin for service popular use cases
    """
    model = ServicePopularUseCase
    extra = 1
    # FIXED: Changed 'title' to 'use_case' to match model field
    fields = ['use_case', 'description']


class ServiceFAQInline(admin.TabularInline):
    """
    Inline admin for service FAQs
    """
    model = ServiceFAQ
    extra = 1
    fields = ['question', 'answer', 'sort_order']
    ordering = ['sort_order']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """
    Admin interface for Service model
    """
    
    list_display = [
        'name',
        'category',
        'subcategory',
        'pricing_model_display',
        'starting_at_display',
        'featured_display',
        'active_display',
        'pricing_tiers_count',
        'date_created'
    ]
    list_filter = [
        'pricing_model',
        'featured',
        'active',
        'category',
        'subcategory',
        'currency',
        'date_created'
    ]
    search_fields = ['name', 'description', 'category', 'subcategory']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = [
        'id',
        'date_created',
        'date_updated',
        'pricing_tiers_count',
        'process_steps_count',
        'deliverables_count',
        'tools_count',
        'faqs_count'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'subcategory')
        }),
        ('Content', {
            'fields': ('description', 'short_description')
        }),
        ('Media', {
            'fields': ('img_url', 'banner_url', 'icon_url'),
            'classes': ('collapse',)
        }),
        ('Pricing', {
            'fields': ('pricing_model', 'starting_at', 'currency', 'timeline')
        }),
        ('Settings', {
            'fields': ('featured', 'active', 'sort_order'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'pricing_tiers_count', 'process_steps_count', 
                'deliverables_count', 'tools_count', 'faqs_count'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [
        ServicePricingTierInline,
        ServiceProcessStepInline,
        ServiceDeliverableInline,
        ServiceToolInline,
        ServicePopularUsecaseInline,
        ServiceFAQInline
    ]
    
    def pricing_model_display(self, obj):
        """Display pricing model with color coding"""
        colors = {
            'fixed': '#28a745',      # Green
            'tiered': '#17a2b8',     # Blue  
            'custom': '#ffc107',     # Yellow
            'hourly': '#fd7e14',     # Orange
            'per-page': '#6f42c1'    # Purple
        }
        color = colors.get(obj.pricing_model, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.get_pricing_model_display()
        )
    pricing_model_display.short_description = 'Pricing Model'
    
    def starting_at_display(self, obj):
        """Display starting price with currency"""
        if obj.starting_at:
            return format_html(
                '<strong>{} {}</strong>',
                obj.currency, obj.starting_at
            )
        return '-'
    starting_at_display.short_description = 'Starting Price'
    
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
    
    def pricing_tiers_count(self, obj):
        """Count of pricing tiers"""
        return obj.pricing_tiers.count()
    pricing_tiers_count.short_description = 'Pricing Tiers'
    
    def process_steps_count(self, obj):
        """Count of process steps"""
        return obj.process_steps.count()
    process_steps_count.short_description = 'Process Steps'
    
    def deliverables_count(self, obj):
        """Count of deliverables"""
        return obj.deliverables.count()
    deliverables_count.short_description = 'Deliverables'
    
    def tools_count(self, obj):
        """Count of tools"""
        return obj.tools.count()
    tools_count.short_description = 'Tools'
    
    def faqs_count(self, obj):
        """Count of FAQs"""
        return obj.faqs.count()
    faqs_count.short_description = 'FAQs'
    
    actions = ['feature_services', 'unfeature_services', 'activate_services', 'deactivate_services']
    
    def feature_services(self, request, queryset):
        """Feature selected services"""
        updated = queryset.update(featured=True)
        self.message_user(request, f"Successfully featured {updated} service(s).")
    feature_services.short_description = "Feature selected services"
    
    def unfeature_services(self, request, queryset):
        """Unfeature selected services"""
        updated = queryset.update(featured=False)
        self.message_user(request, f"Successfully unfeatured {updated} service(s).")
    unfeature_services.short_description = "Unfeature selected services"
    
    def activate_services(self, request, queryset):
        """Activate selected services"""
        updated = queryset.update(active=True)
        self.message_user(request, f"Successfully activated {updated} service(s).")
    activate_services.short_description = "Activate selected services"
    
    def deactivate_services(self, request, queryset):
        """Deactivate selected services"""
        updated = queryset.update(active=False)
        self.message_user(request, f"Successfully deactivated {updated} service(s).")
    deactivate_services.short_description = "Deactivate selected services"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).prefetch_related(
            'pricing_tiers', 'process_steps', 'deliverables', 
            'tools', 'popular_usecases', 'faqs'
        )


@admin.register(ServicePricingTier)
class ServicePricingTierAdmin(admin.ModelAdmin):
    """
    Admin interface for ServicePricingTier model
    """
    
    list_display = [
        'name',
        'service_name',
        'price_display',
        'recommended_display',
        'sort_order'
    ]
    list_filter = [
        'recommended',
        'currency',
        'service__category'
    ]
    search_fields = [
        'name',
        'unit',  # FIXED: Changed 'description' to 'unit' as model has no description field
        'service__name'
    ]
    raw_id_fields = ['service']
    ordering = ['service', 'sort_order']
    
    def service_name(self, obj):
        """Display service name with link"""
        if obj.service:
            url = reverse('admin:services_service_change', args=[obj.service.pk])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'
    
    def price_display(self, obj):
        """Display price with currency"""
        return format_html(
            '<strong>{} {}</strong>',
            obj.currency, obj.price
        )
    price_display.short_description = 'Price'
    
    def recommended_display(self, obj):
        """Display recommended status"""
        if obj.recommended:
            return format_html('<span style="color: green;">⭐ Recommended</span>')
        return '-'
    recommended_display.short_description = 'Recommended'


@admin.register(ServiceProcessStep)
class ServiceProcessStepAdmin(admin.ModelAdmin):
    """
    Admin interface for ServiceProcessStep model
    """
    
    list_display = [
        'step_order',  # FIXED: Changed 'step_number' to 'step_order'
        'title',
        'service_name',
        'description_preview'
    ]
    list_filter = ['service__category']
    search_fields = ['title', 'description', 'service__name']
    raw_id_fields = ['service']
    ordering = ['service', 'step_order']  # FIXED: Changed 'step_number' to 'step_order'
    
    def service_name(self, obj):
        """Display service name with link"""
        if obj.service:
            url = reverse('admin:services_service_change', args=[obj.service.pk])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'
    
    def description_preview(self, obj):
        """Show truncated description"""
        if obj.description:
            return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
        return '-'
    description_preview.short_description = 'Description Preview'


@admin.register(ServiceDeliverable)
class ServiceDeliverableAdmin(admin.ModelAdmin):
    """
    Admin interface for ServiceDeliverable model
    """
    
    list_display = [
        'description_preview',  # FIXED: Changed 'name' to 'description_preview' as model has no name field
        'service_name',
        'sort_order'
    ]
    list_filter = ['service__category']
    search_fields = ['description', 'service__name']  # FIXED: Changed 'name' to 'description'
    raw_id_fields = ['service']
    ordering = ['service', 'sort_order']
    
    def service_name(self, obj):
        """Display service name with link"""
        if obj.service:
            url = reverse('admin:services_service_change', args=[obj.service.pk])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'
    
    def description_preview(self, obj):
        """Show truncated description"""
        if obj.description:
            return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
        return '-'
    description_preview.short_description = 'Description'  # This serves as the "name"


@admin.register(ServiceTool)
class ServiceToolAdmin(admin.ModelAdmin):
    """
    Admin interface for ServiceTool model
    """
    
    list_display = [
        'tool_name',  # FIXED: Changed 'name' to 'tool_name'
        'service_name',
        'icon_display',
        'tool_url_preview'  # FIXED: Changed 'description_preview' to 'tool_url_preview'
    ]
    list_filter = ['service__category']
    search_fields = ['tool_name', 'tool_url', 'service__name']  # FIXED: Updated field names
    raw_id_fields = ['service']
    
    def service_name(self, obj):
        """Display service name with link"""
        if obj.service:
            url = reverse('admin:services_service_change', args=[obj.service.pk])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'
    
    def icon_display(self, obj):
        """Display tool icon if available"""
        if obj.icon_url:
            return format_html(
                '<img src="{}" style="width: 24px; height: 24px;" alt="{}" />',
                obj.icon_url, obj.tool_name
            )
        return '-'
    icon_display.short_description = 'Icon'
    
    def tool_url_preview(self, obj):
        """Show truncated tool URL"""
        if obj.tool_url:
            return (obj.tool_url[:50] + '...') if len(obj.tool_url) > 50 else obj.tool_url
        return '-'
    tool_url_preview.short_description = 'Tool URL'


@admin.register(ServicePopularUseCase)
class ServicePopularUsecaseAdmin(admin.ModelAdmin):
    """
    Admin interface for ServicePopularUsecase model
    """
    
    list_display = [
        'use_case',  # FIXED: Changed 'title' to 'use_case'
        'service_name',
        'description_preview'
    ]
    list_filter = ['service__category']
    search_fields = ['use_case', 'description', 'service__name']  # FIXED: Changed 'title' to 'use_case'
    raw_id_fields = ['service']
    
    def service_name(self, obj):
        """Display service name with link"""
        if obj.service:
            url = reverse('admin:services_service_change', args=[obj.service.pk])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'
    
    def description_preview(self, obj):
        """Show truncated description"""
        if obj.description:
            return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
        return '-'
    description_preview.short_description = 'Description Preview'


@admin.register(ServiceFAQ)
class ServiceFAQAdmin(admin.ModelAdmin):
    """
    Admin interface for ServiceFAQ model
    """
    
    list_display = [
        'question_preview',
        'service_name',
        'answer_preview',
        'sort_order'
    ]
    list_filter = ['service__category']
    search_fields = ['question', 'answer', 'service__name']
    raw_id_fields = ['service']
    ordering = ['service', 'sort_order']
    
    def service_name(self, obj):
        """Display service name with link"""
        if obj.service:
            url = reverse('admin:services_service_change', args=[obj.service.pk])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'
    
    def question_preview(self, obj):
        """Show truncated question"""
        return (obj.question[:50] + '...') if len(obj.question) > 50 else obj.question
    question_preview.short_description = 'Question'
    
    def answer_preview(self, obj):
        """Show truncated answer"""
        return (obj.answer[:75] + '...') if len(obj.answer) > 75 else obj.answer
    answer_preview.short_description = 'Answer Preview'


# Custom admin site configuration
admin.site.site_header = "Portfolio Services Administration"
admin.site.site_title = "Services Admin"
admin.site.index_title = "Services Management Dashboard"