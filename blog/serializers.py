# blog/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from .models import Tag, BlogPost, BlogPostTag, BlogComment

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """
    Serializer for Tag model
    Used across blog and products
    """
    
    posts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'color', 'posts_count']
        read_only_fields = ['id', 'slug', 'posts_count']
    
    def get_posts_count(self, obj):
        """Return count of published blog posts with this tag"""
        return obj.blog_posts.filter(status='published').count()
    
    def validate_name(self, value):
        """Ensure tag name is unique and properly formatted"""
        if not value.strip():
            raise serializers.ValidationError("Tag name cannot be empty.")
        return value.strip().title()  # Capitalize properly
    
    def validate_color(self, value):
        """Validate hex color code format"""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be a hex code starting with #")
        if value and len(value) != 7:
            raise serializers.ValidationError("Color must be a 7-character hex code (e.g., #FF5733)")
        return value


class TagListSerializer(serializers.ModelSerializer):
    """
    Simplified tag serializer for lists
    """
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'color']


class AuthorSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post authors
    """
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
    
    def get_full_name(self, obj):
        """Return full name or email if names not available"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.email.split('@')[0]  # Use email username as fallback


class BlogCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for blog comments with nested replies
    """
    
    replies = serializers.SerializerMethodField()
    is_reply = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogComment
        fields = [
            'id', 
            'name', 
            'email', 
            'website', 
            'message', 
            'approved',
            'is_reply',
            'parent',
            'replies',
            'date_created'
        ]
        read_only_fields = ['id', 'date_created', 'is_reply', 'replies']
    
    def get_replies(self, obj):
        """Get approved replies to this comment"""
        if obj.replies.exists():
            replies = obj.replies.filter(approved=True).order_by('date_created')
            return BlogCommentSerializer(replies, many=True, context=self.context).data
        return []
    
    def get_is_reply(self, obj):
        """Check if this comment is a reply"""
        return obj.parent is not None
    
    def validate_message(self, value):
        """Ensure message is not empty and has minimum length"""
        if not value.strip():
            raise serializers.ValidationError("Comment message cannot be empty.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Comment must be at least 10 characters long.")
        return value.strip()
    
    def validate_email(self, value):
        """Validate email format if provided"""
        if value and '@' not in value:
            raise serializers.ValidationError("Please provide a valid email address.")
        return value.lower() if value else value


class BlogCommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating blog comments
    Separate from read serializer to avoid nested complexity
    """
    
    class Meta:
        model = BlogComment
        fields = ['name', 'email', 'website', 'message', 'parent']
    
    def validate_message(self, value):
        """Ensure message is not empty and has minimum length"""
        if not value.strip():
            raise serializers.ValidationError("Comment message cannot be empty.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Comment must be at least 10 characters long.")
        return value.strip()


class BlogPostListSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post lists
    Includes essential fields and related data
    """
    
    author = AuthorSerializer(read_only=True)
    tags = TagListSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    reading_time = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 
            'title', 
            'slug', 
            'excerpt', 
            'image_url',
            'author',
            'tags',
            'date_published',
            'category',
            'status',
            'view_count',
            'featured',
            'comments_count',
            'reading_time',
            'date_created'
        ]
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()
    
    def get_reading_time(self, obj):
        """Estimate reading time based on content length (200 words per minute)"""
        if obj.content:
            word_count = len(obj.content.split())
            return max(1, round(word_count / 200))  # Minimum 1 minute
        return 1


class BlogPostDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual blog posts
    Includes full content and nested relationships
    """
    
    author = AuthorSerializer(read_only=True)
    tags = TagListSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    reading_time = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id', 
            'title', 
            'slug', 
            'excerpt',
            'content', 
            'image_url',
            'author',
            'tags',
            'date_published',
            'category',
            'status',
            'view_count',
            'featured',
            'comments',
            'comments_count',
            'reading_time',
            'date_created',
            'date_updated'
        ]
    
    def get_comments(self, obj):
        """Get approved top-level comments with replies"""
        top_level_comments = obj.comments.filter(
            approved=True, 
            parent=None
        ).order_by('date_created')
        return BlogCommentSerializer(top_level_comments, many=True, context=self.context).data
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()
    
    def get_reading_time(self, obj):
        """Estimate reading time based on content length"""
        if obj.content:
            word_count = len(obj.content.split())
            return max(1, round(word_count / 200))
        return 1


class BlogPostCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating blog posts
    Handles tag relationships and business logic
    """
    
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of tag IDs to associate with this post"
    )
    tags = TagListSerializer(many=True, read_only=True)
    author = AuthorSerializer(read_only=True)
    
    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'slug',
            'excerpt',
            'content',
            'image_url',
            'date_published',
            'category',
            'status',
            'featured',
            'tag_ids',
            'tags',
            'author',
            'view_count',
            'date_created',
            'date_updated'
        ]
        read_only_fields = ['id', 'author', 'view_count', 'date_created', 'date_updated']
    
    def validate_title(self, value):
        """Ensure title is unique and not empty"""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        
        # Check for uniqueness (excluding current instance during updates)
        queryset = BlogPost.objects.filter(title__iexact=value.strip())
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A blog post with this title already exists.")
        
        return value.strip()
    
    def validate_excerpt(self, value):
        """Validate excerpt length"""
        if not value.strip():
            raise serializers.ValidationError("Excerpt cannot be empty.")
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Excerpt must be at least 50 characters long.")
        if len(value.strip()) > 500:
            raise serializers.ValidationError("Excerpt cannot exceed 500 characters.")
        return value.strip()
    
    def validate_content(self, value):
        """Validate content length"""
        if not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        if len(value.strip()) < 100:
            raise serializers.ValidationError("Content must be at least 100 characters long.")
        return value.strip()
    
    def validate_tag_ids(self, value):
        """Validate that all tag IDs exist"""
        if value:
            existing_tags = Tag.objects.filter(id__in=value)
            if len(existing_tags) != len(value):
                raise serializers.ValidationError("One or more tag IDs are invalid.")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Auto-set publish date when publishing
        if data.get('status') == 'published' and not data.get('date_published'):
            from django.utils import timezone
            data['date_published'] = timezone.now().date()
        
        # Auto-generate slug if not provided
        if not data.get('slug') and data.get('title'):
            data['slug'] = slugify(data['title'])
        
        return data
    
    def create(self, validated_data):
        """Create blog post with tag relationships"""
        tag_ids = validated_data.pop('tag_ids', [])
        
        # Set author to current user
        validated_data['author'] = self.context['request'].user
        
        blog_post = BlogPost.objects.create(**validated_data)
        
        # Associate tags
        if tag_ids:
            for tag_id in tag_ids:
                BlogPostTag.objects.create(blogpost=blog_post, tag_id=tag_id)
        
        return blog_post
    
    def update(self, instance, validated_data):
        """Update blog post with tag relationships"""
        tag_ids = validated_data.pop('tag_ids', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update tags if provided
        if tag_ids is not None:
            # Clear existing tags
            BlogPostTag.objects.filter(blogpost=instance).delete()
            # Add new tags
            for tag_id in tag_ids:
                BlogPostTag.objects.create(blogpost=instance, tag_id=tag_id)
        
        return instance


class PublicBlogPostListSerializer(serializers.ModelSerializer):
    """
    Public serializer for blog post lists
    Only shows published posts with essential fields
    """
    
    author_name = serializers.SerializerMethodField()
    tags = TagListSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    reading_time = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'slug',
            'excerpt',
            'image_url',
            'author_name',
            'tags',
            'date_published',
            'category',
            'featured',
            'comments_count',
            'reading_time'
        ]
    
    def get_author_name(self, obj):
        """Return author's display name"""
        if obj.author.first_name or obj.author.last_name:
            return f"{obj.author.first_name} {obj.author.last_name}".strip()
        return obj.author.email.split('@')[0]
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()
    
    def get_reading_time(self, obj):
        """Estimate reading time"""
        if obj.content:
            word_count = len(obj.content.split())
            return max(1, round(word_count / 200))
        return 1


class PublicBlogPostDetailSerializer(serializers.ModelSerializer):
    """
    Public serializer for individual blog posts
    Only shows published posts with full content
    """
    
    author_name = serializers.SerializerMethodField()
    tags = TagListSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    reading_time = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'slug',
            'excerpt',
            'content',
            'image_url',
            'author_name',
            'tags',
            'date_published',
            'category',
            'view_count',
            'featured',
            'comments',
            'comments_count',
            'reading_time',
            'date_created'
        ]
    
    def get_author_name(self, obj):
        """Return author's display name"""
        if obj.author.first_name or obj.author.last_name:
            return f"{obj.author.first_name} {obj.author.last_name}".strip()
        return obj.author.email.split('@')[0]
    
    def get_comments(self, obj):
        """Get approved top-level comments with replies"""
        top_level_comments = obj.comments.filter(
            approved=True,
            parent=None
        ).order_by('date_created')
        return BlogCommentSerializer(top_level_comments, many=True, context=self.context).data
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()
    
    def get_reading_time(self, obj):
        """Estimate reading time"""
        if obj.content:
            word_count = len(obj.content.split())
            return max(1, round(word_count / 200))
        return 1


class BlogPostStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for blog post statistics (admin use)
    """
    
    total_comments = serializers.SerializerMethodField()
    approved_comments = serializers.SerializerMethodField()
    pending_comments = serializers.SerializerMethodField()
    reading_time = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'status',
            'featured',
            'view_count',
            'author_name',
            'total_comments',
            'approved_comments',
            'pending_comments',
            'reading_time',
            'date_published',
            'date_created'
        ]
    
    def get_author_name(self, obj):
        """Get author's full name"""
        if obj.author.first_name or obj.author.last_name:
            return f"{obj.author.first_name} {obj.author.last_name}".strip()
        return obj.author.email
    
    def get_total_comments(self, obj):
        """Total comments count"""
        return obj.comments.count()
    
    def get_approved_comments(self, obj):
        """Approved comments count"""
        return obj.comments.filter(approved=True).count()
    
    def get_pending_comments(self, obj):
        """Pending comments count"""
        return obj.comments.filter(approved=False).count()
    
    def get_reading_time(self, obj):
        """Estimate reading time"""
        if obj.content:
            word_count = len(obj.content.split())
            return max(1, round(word_count / 200))
        return 1