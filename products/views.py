# products/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F, Avg, Count, Sum
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend

from .models import Product, ProductReview, ProductPurchase, ProductGalleryImage
from .serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateUpdateSerializer,
    PublicProductListSerializer,
    PublicProductDetailSerializer,
    ProductStatsSerializer,
    ProductReviewSerializer,
    ProductReviewCreateSerializer,
    ProductPurchaseSerializer,
    ProductGalleryImageSerializer
)


class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing products
    
    - Admin users get full CRUD access
    - Public users can only view active products
    - Includes advanced filtering and search
    """
    
    queryset = Product.objects.all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'type', 'featured', 'active', 'creator', 'license_type', 'technologies__name', 'tags__slug']
    search_fields = ['name', 'description', 'short_description', 'category', 'type']
    ordering_fields = ['name', 'price', 'download_count', 'date_created']
    ordering = ['-featured', '-date_created']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action and user"""
        if self.action == 'list':
            if self.request.user.is_staff:
                return ProductListSerializer
            return PublicProductListSerializer
        elif self.action == 'retrieve':
            if self.request.user.is_staff:
                return ProductDetailSerializer
            return PublicProductDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ProductCreateUpdateSerializer
        elif self.action == 'stats':
            return ProductStatsSerializer
        return ProductDetailSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'featured', 'by_category', 'by_type', 'by_technology']:
            return [permissions.AllowAny()]
        elif self.action in ['download', 'add_review']:
            return [permissions.AllowAny()]  # Allow public interactions
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return Product.objects.select_related('creator', 'base_project').prefetch_related(
                'technologies', 'tags', 'gallery_images', 'reviews'
            )
        
        # Public users only see active products
        return Product.objects.filter(active=True).select_related(
            'creator', 'base_project'
        ).prefetch_related('technologies', 'tags', 'gallery_images', 'reviews')
    
    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to increment download count for public users"""
        instance = self.get_object()
        
        # Increment download count for active products (view tracking)
        if instance.active and not request.user.is_staff:
            Product.objects.filter(pk=instance.pk).update(download_count=F('download_count') + 1)
            instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured products"""
        featured_products = self.get_queryset().filter(featured=True)[:6]
        serializer = self.get_serializer(featured_products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get products by category"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'Category parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = self.get_queryset().filter(category__iexact=category)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get products by type"""
        product_type = request.query_params.get('type')
        if not product_type:
            return Response(
                {'detail': 'Type parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = self.get_queryset().filter(type__iexact=product_type)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_technology(self, request):
        """Get products by technology"""
        tech_name = request.query_params.get('technology')
        if not tech_name:
            return Response(
                {'detail': 'Technology parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = self.get_queryset().filter(technologies__name__iexact=tech_name)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_price_range(self, request):
        """Get products within price range"""
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        
        if not min_price and not max_price:
            return Response(
                {'detail': 'At least one price parameter (min_price or max_price) is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        products = self.get_queryset()
        
        if min_price:
            try:
                min_price = float(min_price)
                products = products.filter(price__gte=min_price)
            except ValueError:
                return Response(
                    {'detail': 'Invalid min_price format.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if max_price:
            try:
                max_price = float(max_price)
                products = products.filter(price__lte=max_price)
            except ValueError:
                return Response(
                    {'detail': 'Invalid max_price format.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, slug=None):
        """Toggle featured status of a product"""
        product = self.get_object()
        
        product.featured = not product.featured
        product.save()
        
        status_text = 'featured' if product.featured else 'unfeatured'
        return Response(
            {'detail': f'Product "{product.name}" has been {status_text}.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, slug=None):
        """Toggle active status of a product"""
        product = self.get_object()
        
        product.active = not product.active
        product.save()
        
        status_text = 'activated' if product.active else 'deactivated'
        return Response(
            {'detail': f'Product "{product.name}" has been {status_text}.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def download(self, request, slug=None):
        """Handle product download (requires authentication or purchase)"""
        product = self.get_object()
        
        if not product.active:
            return Response(
                {'detail': 'Product is not available for download.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For free products (price = 0), allow direct download
        if product.price == 0:
            if product.download_url:
                # Increment download count
                Product.objects.filter(pk=product.pk).update(download_count=F('download_count') + 1)
                return Response({
                    'download_url': product.download_url,
                    'license_type': product.license_type,
                    'version': product.version
                })
            else:
                return Response(
                    {'detail': 'Download URL not available.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # For paid products, check if user has purchased
        if request.user.is_authenticated:
            purchase = ProductPurchase.objects.filter(
                product=product,
                client=request.user,
                status='completed'
            ).first()
            
            if purchase:
                if product.download_url:
                    # Increment purchase download count
                    purchase.download_count = F('download_count') + 1
                    purchase.save()
                    
                    return Response({
                        'download_url': product.download_url,
                        'license_key': purchase.license_key,
                        'license_type': product.license_type,
                        'version': product.version
                    })
                else:
                    return Response(
                        {'detail': 'Download URL not available.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        return Response(
            {'detail': 'Purchase required to download this product.'}, 
            status=status.HTTP_402_PAYMENT_REQUIRED
        )
    
    @action(detail=True, methods=['post'])
    def add_review(self, request, slug=None):
        """Add a review to a product"""
        product = self.get_object()
        
        if not product.active:
            return Response(
                {'detail': 'Reviews are only allowed on active products.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has already reviewed this product
        if request.user.is_authenticated:
            existing_review = ProductReview.objects.filter(
                product=product,
                client=request.user
            ).first()
            
            if existing_review:
                return Response(
                    {'detail': 'You have already reviewed this product.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        serializer = ProductReviewCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Create review (not approved by default)
            review = serializer.save(
                product=product,
                client=request.user if request.user.is_authenticated else None,
                approved=False  # Requires admin approval
            )
            
            # Return the created review
            response_serializer = ProductReviewSerializer(review)
            return Response(
                {
                    'detail': 'Review submitted successfully. It will be published after review.',
                    'review': response_serializer.data
                }, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get product statistics (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        products = Product.objects.all()
        serializer = ProductStatsSerializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently created products"""
        limit = int(request.query_params.get('limit', 4))
        recent_products = self.get_queryset()[:limit]
        serializer = self.get_serializer(recent_products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Get top-rated products"""
        limit = int(request.query_params.get('limit', 6))
        
        # Get products with highest average ratings
        products = self.get_queryset().annotate(
            avg_rating=Avg('reviews__rating', filter=Q(reviews__approved=True)),
            reviews_count=Count('reviews', filter=Q(reviews__approved=True))
        ).filter(
            reviews_count__gte=3  # At least 3 reviews
        ).order_by('-avg_rating')[:limit]
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def bestsellers(self, request):
        """Get best-selling products"""
        limit = int(request.query_params.get('limit', 6))
        
        # Get products with most purchases
        products = self.get_queryset().annotate(
            purchase_count=Count('purchases', filter=Q(purchases__status='completed'))
        ).filter(
            purchase_count__gt=0
        ).order_by('-purchase_count')[:limit]
        
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class ProductReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product reviews
    
    - Admin users can manage all reviews
    - Public users can only view approved reviews
    """
    
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'approved', 'rating']
    ordering_fields = ['rating', 'date_created']
    ordering = ['-date_created']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return ProductReview.objects.select_related('product', 'client')
        
        # Public users only see approved reviews
        return ProductReview.objects.filter(
            approved=True
        ).select_related('product', 'client')
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a review"""
        review = self.get_object()
        review.approved = True
        review.save()
        
        return Response(
            {'detail': f'Review by {review.client.email if review.client else "Anonymous"} has been approved.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject (unapprove) a review"""
        review = self.get_object()
        review.approved = False
        review.save()
        
        return Response(
            {'detail': f'Review by {review.client.email if review.client else "Anonymous"} has been rejected.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get pending reviews for admin review"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        pending_reviews = ProductReview.objects.filter(approved=False)
        page = self.paginate_queryset(pending_reviews)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_reviews, many=True)
        return Response(serializer.data)


class ProductPurchaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product purchases
    
    - Admin users can manage all purchases
    - Clients can view their own purchases
    """
    
    queryset = ProductPurchase.objects.all()
    serializer_class = ProductPurchaseSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'client', 'status']
    ordering_fields = ['purchase_amount', 'date_created']
    ordering = ['-date_created']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return ProductPurchase.objects.select_related('product', 'client')
        
        # Users can only see their own purchases
        return ProductPurchase.objects.filter(
            client=self.request.user
        ).select_related('product', 'client')


class ProductGalleryImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing product gallery images
    
    - Admin users can CRUD gallery images
    - Public users can view images
    """
    
    queryset = ProductGalleryImage.objects.all()
    serializer_class = ProductGalleryImageSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product']
    ordering_fields = ['sort_order', 'id']
    ordering = ['product', 'sort_order']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on product visibility"""
        if self.request.user.is_staff:
            return ProductGalleryImage.objects.select_related('product')
        
        # Public users only see images from active products
        return ProductGalleryImage.objects.filter(
            product__active=True
        ).select_related('product')


# Simple API views for specific use cases
from rest_framework import generics


class FeaturedProductsAPIView(generics.ListAPIView):
    """
    Get featured products
    """
    
    serializer_class = PublicProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 6))
        return Product.objects.filter(
            featured=True,
            active=True
        ).select_related('creator').prefetch_related('technologies', 'tags')[:limit]


class RecentProductsAPIView(generics.ListAPIView):
    """
    Get recent products
    """
    
    serializer_class = PublicProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 4))
        return Product.objects.filter(
            active=True
        ).select_related('creator').prefetch_related('technologies', 'tags').order_by('-date_created')[:limit]


class ProductCategoriesAPIView(generics.ListAPIView):
    """
    Get all product categories with counts
    """
    
    permission_classes = [permissions.AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Return categories with product counts"""
        categories = Product.objects.filter(active=True).values('category').annotate(
            count=Count('id'),
            avg_price=Avg('price')
        ).order_by('category')
        
        return Response({
            'categories': list(categories),
            'total_categories': len(categories)
        })


class ProductTypesAPIView(generics.ListAPIView):
    """
    Get all product types with counts
    """
    
    permission_classes = [permissions.AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Return product types with counts"""
        types = Product.objects.filter(active=True).values('type').annotate(
            count=Count('id'),
            avg_price=Avg('price')
        ).order_by('type')
        
        return Response({
            'types': list(types),
            'total_types': len(types)
        })


class RelatedProductsAPIView(generics.ListAPIView):
    """
    Get related products based on technologies and category
    """
    
    serializer_class = PublicProductListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        product_slug = self.kwargs.get('slug')
        try:
            current_product = Product.objects.get(slug=product_slug, active=True)
            # Get products with similar technologies or category
            related_products = Product.objects.filter(
                Q(technologies__in=current_product.technologies.all()) | 
                Q(category=current_product.category),
                active=True
            ).exclude(id=current_product.id).distinct()[:4]
            return related_products
        except Product.DoesNotExist:
            return Product.objects.none()