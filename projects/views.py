# projects/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F, Count
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend

from .models import Technology, Project, ProjectComment, ProjectGalleryImage
from .serializers import (
    TechnologySerializer,
    TechnologyListSerializer,
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateUpdateSerializer,
    PublicProjectListSerializer,
    PublicProjectDetailSerializer,
    ProjectStatsSerializer,
    ProjectCommentSerializer,
    ProjectCommentCreateSerializer,
    ProjectGalleryImageSerializer
)


class TechnologyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing technologies
    
    - Admin users can CRUD technologies
    - Public users can view technologies
    """
    
    queryset = Technology.objects.all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    filterset_fields = ['category']
    search_fields = ['name', 'category']
    ordering_fields = ['name', 'category', 'id']
    ordering = ['category', 'name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TechnologyListSerializer
        return TechnologySerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get technologies grouped by category"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'Category parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        technologies = Technology.objects.filter(category__iexact=category)
        serializer = TechnologyListSerializer(technologies, many=True)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60 * 30))
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular technologies based on project usage"""
        technologies = Technology.objects.filter(
            projects__status='completed'
        ).distinct().annotate(
            project_count=Count('projects')
        ).order_by('-project_count')[:10]
        
        serializer = TechnologyListSerializer(technologies, many=True)
        return Response(serializer.data)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing projects
    
    - Admin users get full CRUD access
    - Public users can only view completed projects
    - Includes advanced filtering and search
    """
    
    queryset = Project.objects.all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'domain', 'status', 'featured', 'client', 'technologies__name']
    search_fields = ['title', 'description', 'content', 'category', 'domain']
    ordering_fields = ['date_created', 'completion_date', 'likes', 'title']
    ordering = ['-date_created']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action and user"""
        if self.action == 'list':
            if self.request.user.is_staff:
                return ProjectListSerializer
            return PublicProjectListSerializer
        elif self.action == 'retrieve':
            if self.request.user.is_staff:
                return ProjectDetailSerializer
            return PublicProjectDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProjectCreateUpdateSerializer
        elif self.action == 'stats':
            return ProjectStatsSerializer
        return ProjectDetailSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'featured', 'by_category', 'by_technology']:
            return [permissions.AllowAny()]
        elif self.action in ['like', 'add_comment']:
            return [permissions.AllowAny()]  # Allow anonymous interactions
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return Project.objects.select_related('client').prefetch_related('technologies', 'gallery_images')
        
        # Public users only see completed projects
        return Project.objects.filter(
            status__in=['completed', 'maintenance']
        ).select_related('client').prefetch_related('technologies', 'gallery_images')
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured projects"""
        featured_projects = self.get_queryset().filter(featured=True)[:6]
        serializer = self.get_serializer(featured_projects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get projects by category"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'Category parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        projects = self.get_queryset().filter(category__iexact=category)
        page = self.paginate_queryset(projects)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_technology(self, request):
        """Get projects by technology"""
        tech_name = request.query_params.get('technology')
        if not tech_name:
            return Response(
                {'detail': 'Technology parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        projects = self.get_queryset().filter(technologies__name__iexact=tech_name)
        page = self.paginate_queryset(projects)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get projects by status"""
        project_status = request.query_params.get('status')
        if not project_status:
            return Response(
                {'detail': 'Status parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        projects = self.get_queryset().filter(status=project_status)
        page = self.paginate_queryset(projects)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def like(self, request, slug=None):
        """Like/unlike a project"""
        project = self.get_object()
        
        # Simple like increment (you could implement user-based likes later)
        Project.objects.filter(pk=project.pk).update(likes=F('likes') + 1)
        project.refresh_from_db()
        
        return Response(
            {
                'detail': f'Project "{project.title}" liked successfully.',
                'likes': project.likes
            }, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, slug=None):
        """Toggle featured status of a project"""
        project = self.get_object()
        
        project.featured = not project.featured
        project.save()
        
        status_text = 'featured' if project.featured else 'unfeatured'
        return Response(
            {'detail': f'Project "{project.title}" has been {status_text}.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, slug=None):
        """Mark project as completed"""
        project = self.get_object()
        
        if project.status == 'completed':
            return Response(
                {'detail': 'Project is already completed.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.utils import timezone
        project.status = 'completed'
        project.completion_date = timezone.now().date()
        project.save()
        
        return Response(
            {'detail': f'Project "{project.title}" has been marked as completed.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, slug=None):
        """Add a comment to a project"""
        project = self.get_object()
        
        serializer = ProjectCommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Create comment (not approved by default)
            comment = serializer.save(
                project=project,
                approved=False  # Requires admin approval
            )
            
            # Return the created comment
            response_serializer = ProjectCommentSerializer(comment)
            return Response(
                {
                    'detail': 'Comment submitted successfully. It will be published after review.',
                    'comment': response_serializer.data
                }, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get project statistics (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        projects = Project.objects.all()
        serializer = ProjectStatsSerializer(projects, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently created projects"""
        limit = int(request.query_params.get('limit', 4))
        recent_projects = self.get_queryset()[:limit]
        serializer = self.get_serializer(recent_projects, many=True)
        return Response(serializer.data)


class ProjectCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing project comments
    
    - Admin users can manage all comments
    - Public users can only view approved comments
    """
    
    queryset = ProjectComment.objects.all()
    serializer_class = ProjectCommentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'approved']
    ordering_fields = ['date_created']
    ordering = ['-date_created']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return ProjectComment.objects.select_related('project')
        
        # Public users only see approved comments
        return ProjectComment.objects.filter(
            approved=True
        ).select_related('project')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a comment"""
        comment = self.get_object()
        comment.approved = True
        comment.save()
        
        return Response(
            {'detail': f'Comment by {comment.name} has been approved.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject (unapprove) a comment"""
        comment = self.get_object()
        comment.approved = False
        comment.save()
        
        return Response(
            {'detail': f'Comment by {comment.name} has been rejected.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending comments for admin review"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_comments = ProjectComment.objects.filter(approved=False)
        page = self.paginate_queryset(pending_comments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_comments, many=True)
        return Response(serializer.data)


class ProjectGalleryImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing project gallery images
    
    - Admin users can CRUD gallery images
    - Public users can view images
    """
    
    queryset = ProjectGalleryImage.objects.all()
    serializer_class = ProjectGalleryImageSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project']
    ordering_fields = ['sort_order', 'id']
    ordering = ['project', 'sort_order']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on project visibility"""
        if self.request.user.is_staff:
            return ProjectGalleryImage.objects.select_related('project')
        
        # Public users only see images from completed/maintenance projects
        return ProjectGalleryImage.objects.filter(
            project__status__in=['completed', 'maintenance']
        ).select_related('project')


# Simple API views for specific use cases
from rest_framework import generics


class FeaturedProjectsAPIView(generics.ListAPIView):
    """
    Get featured projects
    """
    
    serializer_class = PublicProjectListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 6))
        return Project.objects.filter(
            featured=True,
            status__in=['completed', 'maintenance']
        ).select_related('client').prefetch_related('technologies')[:limit]


class RecentProjectsAPIView(generics.ListAPIView):
    """
    Get recent projects
    """
    
    serializer_class = PublicProjectListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 4))
        return Project.objects.filter(
            status__in=['completed', 'maintenance']
        ).select_related('client').prefetch_related('technologies').order_by('-date_created')[:limit]


class RelatedProjectsAPIView(generics.ListAPIView):
    """
    Get related projects based on technologies and category
    """
    
    serializer_class = PublicProjectListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        project_slug = self.kwargs.get('slug')
        try:
            current_project = Project.objects.get(slug=project_slug)
            # Get projects with similar technologies or category
            related_projects = Project.objects.filter(
                Q(technologies__in=current_project.technologies.all()) | 
                Q(category=current_project.category),
                status__in=['completed', 'maintenance']
            ).exclude(id=current_project.id).distinct()[:4]
            return related_projects
        except Project.DoesNotExist:
            return Project.objects.none()