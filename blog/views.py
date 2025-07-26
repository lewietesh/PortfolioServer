# blog/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend

from .models import Tag, BlogPost, BlogComment
from .serializers import (
    TagSerializer,
    TagListSerializer,
    BlogPostListSerializer,
    BlogPostDetailSerializer,
    BlogPostCreateUpdateSerializer,
    PublicBlogPostListSerializer,
    PublicBlogPostDetailSerializer,
    BlogPostStatsSerializer,
    BlogCommentSerializer,
    BlogCommentCreateSerializer
)


class TagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing tags
    
    - Admin users can CRUD tags
    - Public users can view tags
    """
    
    queryset = Tag.objects.all()
    lookup_field = 'slug'
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'id']
    ordering = ['name']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return TagListSerializer
        return TagSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular tags based on published post count"""
        tags = Tag.objects.filter(
            blog_posts__status='published'
        ).distinct().order_by('-blog_posts__view_count')[:10]
        
        serializer = TagListSerializer(tags, many=True)
        return Response(serializer.data)


class BlogPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing blog posts
    
    - Admin users get full CRUD access
    - Public users can only view published posts
    - Includes advanced filtering and search
    """
    
    queryset = BlogPost.objects.all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'status', 'featured', 'author', 'tags__slug']
    search_fields = ['title', 'excerpt', 'content']
    ordering_fields = ['date_published', 'date_created', 'view_count', 'title']
    ordering = ['-date_created']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action and user"""
        if self.action == 'list':
            if self.request.user.is_staff:
                return BlogPostListSerializer
            return PublicBlogPostListSerializer
        elif self.action == 'retrieve':
            if self.request.user.is_staff:
                return BlogPostDetailSerializer
            return PublicBlogPostDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return BlogPostCreateUpdateSerializer
        elif self.action == 'stats':
            return BlogPostStatsSerializer
        return BlogPostDetailSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'featured', 'by_category', 'by_tag']:
            return [permissions.AllowAny()]
        elif self.action in ['like', 'add_comment']:
            return [permissions.AllowAny()]  # Allow anonymous comments
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return BlogPost.objects.select_related('author').prefetch_related('tags')
        
        # Public users only see published posts
        return BlogPost.objects.filter(
            status='published'
        ).select_related('author').prefetch_related('tags')
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to increment view count for public users"""
        instance = self.get_object()
        
        # Increment view count for published posts
        if instance.status == 'published':
            BlogPost.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
            instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured blog posts"""
        featured_posts = self.get_queryset().filter(featured=True)[:6]
        serializer = self.get_serializer(featured_posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get posts by category"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'Category parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        posts = self.get_queryset().filter(category__iexact=category)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_tag(self, request):
        """Get posts by tag slug"""
        tag_slug = request.query_params.get('tag')
        if not tag_slug:
            return Response(
                {'detail': 'Tag parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        posts = self.get_queryset().filter(tags__slug=tag_slug)
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, slug=None):
        """Publish a draft blog post"""
        blog_post = self.get_object()
        
        if blog_post.status == 'published':
            return Response(
                {'detail': 'Blog post is already published.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set publication date and status
        from django.utils import timezone
        blog_post.status = 'published'
        blog_post.date_published = timezone.now().date()
        blog_post.save()
        
        return Response(
            {'detail': f'Blog post "{blog_post.title}" has been published.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, slug=None):
        """Unpublish a blog post"""
        blog_post = self.get_object()
        
        blog_post.status = 'draft'
        blog_post.save()
        
        return Response(
            {'detail': f'Blog post "{blog_post.title}" has been unpublished.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, slug=None):
        """Toggle featured status of a blog post"""
        blog_post = self.get_object()
        
        blog_post.featured = not blog_post.featured
        blog_post.save()
        
        status_text = 'featured' if blog_post.featured else 'unfeatured'
        return Response(
            {'detail': f'Blog post "{blog_post.title}" has been {status_text}.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get blog statistics (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        posts = BlogPost.objects.all()
        serializer = BlogPostStatsSerializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_comment(self, request, slug=None):
        """Add a comment to a blog post"""
        blog_post = self.get_object()
        
        # Only allow comments on published posts
        if blog_post.status != 'published':
            return Response(
                {'detail': 'Comments are only allowed on published posts.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BlogCommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Create comment (not approved by default)
            comment = serializer.save(
                blogpost=blog_post,
                approved=False  # Requires admin approval
            )
            
            # Return the created comment
            response_serializer = BlogCommentSerializer(comment)
            return Response(
                {
                    'detail': 'Comment submitted successfully. It will be published after review.',
                    'comment': response_serializer.data
                }, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BlogCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing blog comments
    
    - Admin users can manage all comments
    - Public users can only view approved comments
    """
    
    queryset = BlogComment.objects.all()
    serializer_class = BlogCommentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['blogpost', 'approved', 'parent']
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
            return BlogComment.objects.select_related('blogpost')
        
        # Public users only see approved comments
        return BlogComment.objects.filter(
            approved=True
        ).select_related('blogpost')
    
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
        
        pending_comments = BlogComment.objects.filter(approved=False)
        page = self.paginate_queryset(pending_comments)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_comments, many=True)
        return Response(serializer.data)


# Simple API views for specific use cases
from rest_framework import generics


class LatestBlogPostsAPIView(generics.ListAPIView):
    """
    Get latest published blog posts
    """
    
    serializer_class = PublicBlogPostListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 5))
        return BlogPost.objects.filter(
            status='published'
        ).select_related('author').prefetch_related('tags')[:limit]


class RelatedBlogPostsAPIView(generics.ListAPIView):
    """
    Get related blog posts based on tags
    """
    
    serializer_class = PublicBlogPostListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        post_slug = self.kwargs.get('slug')
        try:
            current_post = BlogPost.objects.get(slug=post_slug, status='published')
            # Get posts with similar tags
            related_posts = BlogPost.objects.filter(
                tags__in=current_post.tags.all(),
                status='published'
            ).exclude(id=current_post.id).distinct()[:4]
            return related_posts
        except BlogPost.DoesNotExist:
            return BlogPost.objects.none()