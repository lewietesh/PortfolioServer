# blog/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count
from .models import Tag, BlogPost, BlogComment, BlogPostTag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Admin interface for Tag model
    """
    
    list_display = ['name', 'slug', 'color_display', 'posts_count', 'id']
    list_filter = ['color']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['posts_count']
    
    def color_display(self, obj):
        """Display color as a colored box"""
        if obj.color:
            return format_html(
                '<div style="width: 30px; height: 20px; background-color: {}; '
                'border: 1px solid #ccc; display: inline-block;"></div> {}',
                obj.color, obj.color
            )
        return '-'
    color_display.short_description = 'Color'
    
    def posts_count(self, obj):
        """Count of blog posts using this tag"""
        return obj.blog_posts.filter(status='published').count()
    posts_count.short_description = 'Published Posts'
    
    def get_queryset(self, request):
        """Optimize queryset with post counts"""
        return super().get_queryset(request).annotate(
            blog_posts_count=Count('blog_posts')
        )


class BlogPostTagInline(admin.TabularInline):
    """
    Inline admin for blog post tags
    """
    model = BlogPostTag
    extra = 1
    autocomplete_fields = ['tag']


class BlogCommentInline(admin.TabularInline):
    """
    Inline admin for blog comments
    """
    model = BlogComment
    extra = 0
    readonly_fields = ['name', 'email', 'message', 'date_created', 'approved']
    fields = ['name', 'email', 'message', 'approved', 'date_created']
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        """Disable adding comments through inline"""
        return False


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """
    Admin interface for BlogPost model
    """
    
    list_display = [
        'title', 
        'author', 
        'status_display', 
        'featured_display',
        'category',
        'view_count',
        'comments_count',
        'date_published',
        'date_created'
    ]
    list_filter = [
        'status', 
        'featured', 
        'category', 
        'author', 
        'date_published',
        'date_created',
        # Removed 'tags' from list_filter since it has a through model
    ]
    search_fields = ['title', 'excerpt', 'content', 'author__email']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = [
        'id', 
        'view_count', 
        'date_created', 
        'date_updated',
        'comments_count',
        'reading_time'
    ]
    # Removed filter_horizontal for tags since it has a through model
    inlines = [BlogPostTagInline, BlogCommentInline]  # Added BlogPostTagInline
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'author', 'category')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'image_url')
        }),
        ('Publishing', {
            'fields': ('status', 'date_published', 'featured'),
            'classes': ('collapse',)
        }),
        # Removed 'Tags & Categories' fieldset since tags can't be in fieldsets with through model
        ('Statistics', {
            'fields': ('view_count', 'comments_count', 'reading_time'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'date_created', 'date_updated'),
            'classes': ('collapse',)
        }),
    )
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'draft': '#ffc107',      # Yellow
            'published': '#28a745',   # Green
            'archived': '#6c757d'     # Gray
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: bold;">● {}</span>',
            color, obj.status.title()
        )
    status_display.short_description = 'Status'
    
    def featured_display(self, obj):
        """Display featured status"""
        if obj.featured:
            return format_html('<span style="color: gold;">⭐ Featured</span>')
        return '-'
    featured_display.short_description = 'Featured'
    
    def comments_count(self, obj):
        """Count of approved comments"""
        return obj.comments.filter(approved=True).count()
    comments_count.short_description = 'Comments'
    
    def reading_time(self, obj):
        """Estimate reading time"""
        if obj.content:
            word_count = len(obj.content.split())
            return f"{max(1, round(word_count / 200))} min"
        return "0 min"
    reading_time.short_description = 'Reading Time'
    
    actions = ['publish_posts', 'unpublish_posts', 'feature_posts', 'unfeature_posts']
    
    def publish_posts(self, request, queryset):
        """Publish selected blog posts"""
        from django.utils import timezone
        updated = queryset.update(
            status='published',
            date_published=timezone.now().date()
        )
        self.message_user(request, f"Successfully published {updated} blog post(s).")
    publish_posts.short_description = "Publish selected blog posts"
    
    def unpublish_posts(self, request, queryset):
        """Unpublish selected blog posts"""
        updated = queryset.update(status='draft')
        self.message_user(request, f"Successfully unpublished {updated} blog post(s).")
    unpublish_posts.short_description = "Unpublish selected blog posts"
    
    def feature_posts(self, request, queryset):
        """Feature selected blog posts"""
        updated = queryset.update(featured=True)
        self.message_user(request, f"Successfully featured {updated} blog post(s).")
    feature_posts.short_description = "Feature selected blog posts"
    
    def unfeature_posts(self, request, queryset):
        """Unfeature selected blog posts"""
        updated = queryset.update(featured=False)
        self.message_user(request, f"Successfully unfeatured {updated} blog post(s).")
    unfeature_posts.short_description = "Unfeature selected blog posts"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related(
            'author'
        ).prefetch_related('tags', 'comments')


# Custom list filter for top-level vs reply comments
class CommentTypeFilter(admin.SimpleListFilter):
    """
    Custom filter to distinguish between top-level comments and replies
    """
    title = 'comment type'
    parameter_name = 'comment_type'
    
    def lookups(self, request, model_admin):
        return (
            ('top_level', 'Top-level comments'),
            ('replies', 'Replies'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'top_level':
            return queryset.filter(parent__isnull=True)
        elif self.value() == 'replies':
            return queryset.filter(parent__isnull=False)
        return queryset


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    """
    Admin interface for BlogComment model
    """
    
    list_display = [
        'name',
        'email', 
        'blogpost_title',
        'message_preview',
        'approved_display',
        'is_reply_display',
        'date_created'
    ]
    list_filter = [
        'approved', 
        'date_created',
        'blogpost__category',
        CommentTypeFilter,  # Using custom filter instead of 'parent__isnull'
    ]
    search_fields = [
        'name', 
        'email', 
        'message', 
        'blogpost__title'
    ]
    readonly_fields = [
        'id', 
        'date_created',
        'blogpost_link',
        'parent_comment_link'
    ]
    raw_id_fields = ['blogpost', 'parent']
    
    fieldsets = (
        ('Comment Details', {
            'fields': ('name', 'email', 'website', 'message')
        }),
        ('Relationship', {
            'fields': ('blogpost_link', 'parent_comment_link'),
            'classes': ('collapse',)
        }),
        ('Moderation', {
            'fields': ('approved',)
        }),
        ('Metadata', {
            'fields': ('id', 'date_created'),
            'classes': ('collapse',)
        }),
    )
    
    def blogpost_title(self, obj):
        """Display blog post title with link"""
        if obj.blogpost:
            url = reverse('admin:blog_blogpost_change', args=[obj.blogpost.pk])
            return format_html('<a href="{}">{}</a>', url, obj.blogpost.title)
        return '-'
    blogpost_title.short_description = 'Blog Post'
    
    def message_preview(self, obj):
        """Show truncated message in list view"""
        return (obj.message[:75] + '...') if len(obj.message) > 75 else obj.message
    message_preview.short_description = 'Message Preview'
    
    def approved_display(self, obj):
        """Display approval status with color coding"""
        if obj.approved:
            return format_html('<span style="color: green;">✓ Approved</span>')
        return format_html('<span style="color: red;">✗ Pending</span>')
    approved_display.short_description = 'Status'
    
    def is_reply_display(self, obj):
        """Show if comment is a reply"""
        return obj.parent is not None
    is_reply_display.boolean = True
    is_reply_display.short_description = 'Is Reply'
    
    def blogpost_link(self, obj):
        """Link to parent blog post"""
        if obj.blogpost:
            url = reverse('admin:blog_blogpost_change', args=[obj.blogpost.pk])
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.blogpost.title)
        return '-'
    blogpost_link.short_description = 'Blog Post'
    
    def parent_comment_link(self, obj):
        """Link to parent comment if this is a reply"""
        if obj.parent:
            url = reverse('admin:blog_blogcomment_change', args=[obj.parent.pk])
            return format_html(
                '<a href="{}" target="_blank">Reply to: {}</a>', 
                url, obj.parent.name
            )
        return 'Top-level comment'
    parent_comment_link.short_description = 'Parent Comment'
    
    actions = ['approve_comments', 'reject_comments', 'delete_spam']
    
    def approve_comments(self, request, queryset):
        """Approve selected comments"""
        updated = queryset.update(approved=True)
        self.message_user(request, f"Successfully approved {updated} comment(s).")
    approve_comments.short_description = "Approve selected comments"
    
    def reject_comments(self, request, queryset):
        """Reject selected comments"""
        updated = queryset.update(approved=False)
        self.message_user(request, f"Successfully rejected {updated} comment(s).")
    reject_comments.short_description = "Reject selected comments"
    
    def delete_spam(self, request, queryset):
        """Delete selected comments (for spam)"""
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"Successfully deleted {count} comment(s).")
    delete_spam.short_description = "Delete selected comments (spam)"
    
    def get_queryset(self, request):
        """Optimize queryset with related data"""
        return super().get_queryset(request).select_related(
            'blogpost', 'parent'
        ).order_by('-date_created')


# Custom admin site configuration
admin.site.site_header = "Portfolio Blog Administration"
admin.site.site_title = "Blog Admin"
admin.site.index_title = "Blog Management Dashboard"