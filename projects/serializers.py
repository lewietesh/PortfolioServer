# projects/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from .models import Technology, Project, ProjectGalleryImage, ProjectTechnology, ProjectComment

User = get_user_model()


class TechnologySerializer(serializers.ModelSerializer):
    """
    Serializer for Technology model
    Used across projects and products
    """
    
    projects_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Technology
        fields = ['id', 'name', 'icon_url', 'category', 'projects_count']
        read_only_fields = ['id', 'projects_count']
    
    def get_projects_count(self, obj):
        """Return count of projects using this technology"""
        return obj.projects.filter(status='completed').count()
    
    def validate_name(self, value):
        """Ensure technology name is unique and properly formatted"""
        if not value.strip():
            raise serializers.ValidationError("Technology name cannot be empty.")
        return value.strip().title()
    
    def validate_icon_url(self, value):
        """Validate icon URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Icon URL must be a valid HTTP/HTTPS URL.")
        return value


class TechnologyListSerializer(serializers.ModelSerializer):
    """
    Simplified technology serializer for lists
    """
    
    class Meta:
        model = Technology
        fields = ['id', 'name', 'icon_url', 'category']


class ClientSerializer(serializers.ModelSerializer):
    """
    Serializer for project clients
    """
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name']
    
    def get_full_name(self, obj):
        """Return full name or email if names not available"""
        if obj.first_name or obj.last_name:
            return f"{obj.first_name} {obj.last_name}".strip()
        return obj.email.split('@')[0]


class ProjectGalleryImageSerializer(serializers.ModelSerializer):
    """
    Serializer for project gallery images
    """
    
    class Meta:
        model = ProjectGalleryImage
        fields = ['id', 'image_url', 'alt_text', 'sort_order']
        read_only_fields = ['id']
    
    def validate_image_url(self, value):
        """Validate image URL format"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Image URL must be a valid HTTP/HTTPS URL.")
        return value


class ProjectCommentSerializer(serializers.ModelSerializer):
    """
    Serializer for project comments
    """
    
    class Meta:
        model = ProjectComment
        fields = [
            'id',
            'name',
            'email',
            'message',
            'approved',
            'date_created'
        ]
        read_only_fields = ['id', 'date_created']
    
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


class ProjectCommentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating project comments
    """
    
    class Meta:
        model = ProjectComment
        fields = ['name', 'email', 'message']
    
    def validate_message(self, value):
        """Ensure message is not empty and has minimum length"""
        if not value.strip():
            raise serializers.ValidationError("Comment message cannot be empty.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Comment must be at least 10 characters long.")
        return value.strip()


class ProjectListSerializer(serializers.ModelSerializer):
    """
    Serializer for project lists
    Includes essential fields and related data
    """
    
    client = ClientSerializer(read_only=True)
    technologies = TechnologyListSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    gallery_images_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'domain',
            'client',
            'image_url',
            'description',
            'url',
            'repository_url',
            'likes',
            'featured',
            'completion_date',
            'status',
            'technologies',
            'comments_count',
            'gallery_images_count',
            'date_created'
        ]
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()
    
    def get_gallery_images_count(self, obj):
        """Return count of gallery images"""
        return obj.gallery_images.count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual projects
    Includes full content and nested relationships
    """
    
    client = ClientSerializer(read_only=True)
    technologies = TechnologyListSerializer(many=True, read_only=True)
    gallery_images = ProjectGalleryImageSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'domain',
            'client',
            'image_url',
            'description',
            'content',
            'url',
            'repository_url',
            'likes',
            'featured',
            'completion_date',
            'status',
            'technologies',
            'gallery_images',
            'comments',
            'comments_count',
            'date_created',
            'date_updated'
        ]
    
    def get_comments(self, obj):
        """Get approved comments"""
        approved_comments = obj.comments.filter(approved=True).order_by('date_created')
        return ProjectCommentSerializer(approved_comments, many=True, context=self.context).data
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating projects
    Handles technology relationships and business logic
    """
    
    technology_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
        help_text="List of technology IDs to associate with this project"
    )
    gallery_images_data = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text="List of gallery image objects with image_url, alt_text, sort_order"
    )
    
    technologies = TechnologyListSerializer(many=True, read_only=True)
    client = ClientSerializer(read_only=True)
    gallery_images = ProjectGalleryImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'domain',
            'client',
            'image_url',
            'description',
            'content',
            'url',
            'repository_url',
            'featured',
            'completion_date',
            'status',
            'technology_ids',
            'gallery_images_data',
            'technologies',
            'gallery_images',
            'likes',
            'date_created',
            'date_updated'
        ]
        read_only_fields = ['id', 'likes', 'date_created', 'date_updated']
    
    def validate_title(self, value):
        """Ensure title is unique and not empty"""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        
        # Check for uniqueness (excluding current instance during updates)
        queryset = Project.objects.filter(title__iexact=value.strip())
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A project with this title already exists.")
        
        return value.strip()
    
    def validate_description(self, value):
        """Validate description length"""
        if not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Description must be at least 50 characters long.")
        return value.strip()
    
    def validate_url(self, value):
        """Validate project URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Project URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_repository_url(self, value):
        """Validate repository URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Repository URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_technology_ids(self, value):
        """Validate that all technology IDs exist"""
        if value:
            existing_technologies = Technology.objects.filter(id__in=value)
            if len(existing_technologies) != len(value):
                raise serializers.ValidationError("One or more technology IDs are invalid.")
        return value
    
    def validate_gallery_images_data(self, value):
        """Validate gallery images data structure"""
        if not value:
            return value
        
        for i, image_data in enumerate(value):
            if not isinstance(image_data, dict):
                raise serializers.ValidationError(f"Gallery image {i+1} must be an object.")
            
            if 'image_url' not in image_data:
                raise serializers.ValidationError(f"Gallery image {i+1} must have 'image_url' field.")
            
            if not image_data['image_url'].startswith(('http://', 'https://')):
                raise serializers.ValidationError(f"Gallery image {i+1} URL must be a valid HTTP/HTTPS URL.")
        
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Auto-generate slug if not provided
        if not data.get('slug') and data.get('title'):
            data['slug'] = slugify(data['title'])
        
        # Set completion date when status changes to completed
        if data.get('status') == 'completed' and not data.get('completion_date'):
            from django.utils import timezone
            data['completion_date'] = timezone.now().date()
        
        return data
    
    def create(self, validated_data):
        """Create project with technology and gallery relationships"""
        technology_ids = validated_data.pop('technology_ids', [])
        gallery_images_data = validated_data.pop('gallery_images_data', [])
        
        project = Project.objects.create(**validated_data)
        
        # Associate technologies
        if technology_ids:
            for tech_id in technology_ids:
                ProjectTechnology.objects.create(project=project, technology_id=tech_id)
        
        # Create gallery images
        if gallery_images_data:
            for image_data in gallery_images_data:
                ProjectGalleryImage.objects.create(
                    project=project,
                    image_url=image_data['image_url'],
                    alt_text=image_data.get('alt_text', ''),
                    sort_order=image_data.get('sort_order', 0)
                )
        
        return project
    
    def update(self, instance, validated_data):
        """Update project with technology and gallery relationships"""
        technology_ids = validated_data.pop('technology_ids', None)
        gallery_images_data = validated_data.pop('gallery_images_data', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update technologies if provided
        if technology_ids is not None:
            # Clear existing technologies
            ProjectTechnology.objects.filter(project=instance).delete()
            # Add new technologies
            for tech_id in technology_ids:
                ProjectTechnology.objects.create(project=instance, technology_id=tech_id)
        
        # Update gallery images if provided
        if gallery_images_data is not None:
            # Clear existing gallery images
            ProjectGalleryImage.objects.filter(project=instance).delete()
            # Add new gallery images
            for image_data in gallery_images_data:
                ProjectGalleryImage.objects.create(
                    project=instance,
                    image_url=image_data['image_url'],
                    alt_text=image_data.get('alt_text', ''),
                    sort_order=image_data.get('sort_order', 0)
                )
        
        return instance


class PublicProjectListSerializer(serializers.ModelSerializer):
    """
    Public serializer for project lists
    Only essential fields for portfolio display
    """
    
    client_name = serializers.SerializerMethodField()
    technologies = TechnologyListSerializer(many=True, read_only=True)
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'domain',
            'client_name',
            'image_url',
            'description',
            'url',
            'repository_url',
            'likes',
            'featured',
            'completion_date',
            'status',
            'technologies',
            'comments_count'
        ]
    
    def get_client_name(self, obj):
        """Return client's display name or 'Personal Project'"""
        if obj.client:
            if obj.client.first_name or obj.client.last_name:
                return f"{obj.client.first_name} {obj.client.last_name}".strip()
            return obj.client.email.split('@')[0]
        return "Personal Project"
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()


class PublicProjectDetailSerializer(serializers.ModelSerializer):
    """
    Public serializer for individual projects
    Full project information for portfolio display
    """
    
    client_name = serializers.SerializerMethodField()
    technologies = TechnologyListSerializer(many=True, read_only=True)
    gallery_images = ProjectGalleryImageSerializer(many=True, read_only=True)
    comments = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'slug',
            'category',
            'domain',
            'client_name',
            'image_url',
            'description',
            'content',
            'url',
            'repository_url',
            'likes',
            'featured',
            'completion_date',
            'status',
            'technologies',
            'gallery_images',
            'comments',
            'comments_count',
            'date_created'
        ]
    
    def get_client_name(self, obj):
        """Return client's display name or 'Personal Project'"""
        if obj.client:
            if obj.client.first_name or obj.client.last_name:
                return f"{obj.client.first_name} {obj.client.last_name}".strip()
            return obj.client.email.split('@')[0]
        return "Personal Project"
    
    def get_comments(self, obj):
        """Get approved comments"""
        approved_comments = obj.comments.filter(approved=True).order_by('date_created')
        return ProjectCommentSerializer(approved_comments, many=True, context=self.context).data
    
    def get_comments_count(self, obj):
        """Return count of approved comments"""
        return obj.comments.filter(approved=True).count()


class ProjectStatsSerializer(serializers.ModelSerializer):
    """
    Serializer for project statistics (admin use)
    """
    
    total_comments = serializers.SerializerMethodField()
    approved_comments = serializers.SerializerMethodField()
    pending_comments = serializers.SerializerMethodField()
    technologies_count = serializers.SerializerMethodField()
    gallery_images_count = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'status',
            'featured',
            'likes',
            'client_name',
            'total_comments',
            'approved_comments',
            'pending_comments',
            'technologies_count',
            'gallery_images_count',
            'completion_date',
            'date_created'
        ]
    
    def get_client_name(self, obj):
        """Get client's name"""
        if obj.client:
            if obj.client.first_name or obj.client.last_name:
                return f"{obj.client.first_name} {obj.client.last_name}".strip()
            return obj.client.email
        return "Personal Project"
    
    def get_total_comments(self, obj):
        """Total comments count"""
        return obj.comments.count()
    
    def get_approved_comments(self, obj):
        """Approved comments count"""
        return obj.comments.filter(approved=True).count()
    
    def get_pending_comments(self, obj):
        """Pending comments count"""
        return obj.comments.filter(approved=False).count()
    
    def get_technologies_count(self, obj):
        """Technologies count"""
        return obj.technologies.count()
    
    def get_gallery_images_count(self, obj):
        """Gallery images count"""
        return obj.gallery_images.count()