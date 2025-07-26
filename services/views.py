# services/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Min, Max, Avg, Count
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Service, ServicePricingTier, ServiceFeature, ServiceProcessStep,
    ServiceDeliverable, ServiceTool, ServicePopularUseCase, ServiceFAQ
)
from .serializers import (
    ServiceListSerializer,
    ServiceDetailSerializer,
    ServiceCreateUpdateSerializer,
    PublicServiceListSerializer,
    PublicServiceDetailSerializer,
    ServiceStatsSerializer,
    ServicePricingTierSerializer,
    ServiceFeatureSerializer,
    ServiceProcessStepSerializer,
    ServiceDeliverableSerializer,
    ServiceToolSerializer,
    ServicePopularUsecaseSerializer,
    ServiceFAQSerializer
)


class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing services
    
    - Admin users get full CRUD access
    - Public users can only view active services
    - Includes advanced filtering and search
    """
    
    queryset = Service.objects.all()
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'subcategory', 'pricing_model', 'featured', 'active']
    search_fields = ['name', 'description', 'category', 'subcategory']
    ordering_fields = ['name', 'starting_at', 'date_created', 'timeline']
    ordering = ['-featured', 'starting_at']
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action and user"""
        if self.action == 'list':
            if self.request.user.is_staff:
                return ServiceListSerializer
            return PublicServiceListSerializer
        elif self.action == 'retrieve':
            if self.request.user.is_staff:
                return ServiceDetailSerializer
            return PublicServiceDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ServiceCreateUpdateSerializer
        elif self.action == 'stats':
            return ServiceStatsSerializer
        return ServiceDetailSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'featured', 'by_category', 'by_pricing_model', 'by_price_range', 'pricing_overview']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return Service.objects.prefetch_related(
                'pricing_tiers', 'process_steps', 'deliverables', 
                'tools', 'popular_usecases', 'faqs'
            )
        
        # Public users only see active services
        return Service.objects.filter(active=True).prefetch_related(
            'pricing_tiers', 'process_steps', 'deliverables', 
            'tools', 'popular_usecases', 'faqs'
        )
    
    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured services"""
        featured_services = self.get_queryset().filter(featured=True)[:6]
        serializer = self.get_serializer(featured_services, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get services by category"""
        category = request.query_params.get('category')
        if not category:
            return Response(
                {'detail': 'Category parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        services = self.get_queryset().filter(category__iexact=category)
        page = self.paginate_queryset(services)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_pricing_model(self, request):
        """Get services by pricing model"""
        pricing_model = request.query_params.get('pricing_model')
        if not pricing_model:
            return Response(
                {'detail': 'Pricing model parameter is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        services = self.get_queryset().filter(pricing_model=pricing_model)
        page = self.paginate_queryset(services)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_price_range(self, request):
        """Get services within price range"""
        min_price = request.query_params.get('min_price')
        max_price = request.query_params.get('max_price')
        
        if not min_price and not max_price:
            return Response(
                {'detail': 'At least one price parameter (min_price or max_price) is required.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        services = self.get_queryset()
        
        if min_price:
            try:
                min_price = float(min_price)
                services = services.filter(starting_at__gte=min_price)
            except ValueError:
                return Response(
                    {'detail': 'Invalid min_price format.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if max_price:
            try:
                max_price = float(max_price)
                services = services.filter(starting_at__lte=max_price)
            except ValueError:
                return Response(
                    {'detail': 'Invalid max_price format.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        page = self.paginate_queryset(services)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def toggle_featured(self, request, slug=None):
        """Toggle featured status of a service"""
        service = self.get_object()
        
        service.featured = not service.featured
        service.save()
        
        status_text = 'featured' if service.featured else 'unfeatured'
        return Response(
            {'detail': f'Service "{service.name}" has been {status_text}.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, slug=None):
        """Toggle active status of a service"""
        service = self.get_object()
        
        service.active = not service.active
        service.save()
        
        status_text = 'activated' if service.active else 'deactivated'
        return Response(
            {'detail': f'Service "{service.name}" has been {status_text}.'}, 
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get service statistics (admin only)"""
        if not request.user.is_staff:
            return Response(
                {'detail': 'Permission denied.'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        services = Service.objects.all()
        serializer = ServiceStatsSerializer(services, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pricing_overview(self, request):
        """Get pricing overview across all services"""
        services = self.get_queryset()
        
        pricing_stats = services.aggregate(
            min_price=Min('starting_at'),
            max_price=Max('starting_at'),
            avg_price=Avg('starting_at'),
            total_services=Count('id')
        )
        
        # Group by pricing model
        pricing_models = services.values('pricing_model').annotate(
            count=Count('id'),
            avg_price=Avg('starting_at')
        ).order_by('pricing_model')
        
        # Group by category
        categories = services.values('category').annotate(
            count=Count('id'),
            avg_price=Avg('starting_at')
        ).order_by('category')
        
        return Response({
            'overall_stats': pricing_stats,
            'by_pricing_model': list(pricing_models),
            'by_category': list(categories)
        })


class ServicePricingTierViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service pricing tiers
    """
    
    queryset = ServicePricingTier.objects.all()
    serializer_class = ServicePricingTierSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['service', 'recommended']
    ordering_fields = ['price', 'sort_order']
    ordering = ['service', 'sort_order']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on service visibility"""
        if self.request.user.is_staff:
            return ServicePricingTier.objects.select_related('service')
        
        # Public users only see tiers from active services
        return ServicePricingTier.objects.filter(
            service__active=True
        ).select_related('service')


class ServiceFeatureViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service features
    """
    
    queryset = ServiceFeature.objects.all()
    serializer_class = ServiceFeatureSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'id']
    ordering = ['name']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


class ServiceProcessStepViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service process steps
    """
    
    queryset = ServiceProcessStep.objects.all()
    serializer_class = ServiceProcessStepSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['service']
    ordering_fields = ['step_number', 'id']
    ordering = ['service', 'step_number']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on service visibility"""
        if self.request.user.is_staff:
            return ServiceProcessStep.objects.select_related('service')
        
        # Public users only see steps from active services
        return ServiceProcessStep.objects.filter(
            service__active=True
        ).select_related('service')


class ServiceDeliverableViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service deliverables
    """
    
    queryset = ServiceDeliverable.objects.all()
    serializer_class = ServiceDeliverableSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['service']
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on service visibility"""
        if self.request.user.is_staff:
            return ServiceDeliverable.objects.select_related('service')
        
        # Public users only see deliverables from active services
        return ServiceDeliverable.objects.filter(
            service__active=True
        ).select_related('service')


class ServiceToolViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service tools
    """
    
    queryset = ServiceTool.objects.all()
    serializer_class = ServiceToolSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['service']
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on service visibility"""
        if self.request.user.is_staff:
            return ServiceTool.objects.select_related('service')
        
        # Public users only see tools from active services
        return ServiceTool.objects.filter(
            service__active=True
        ).select_related('service')


class ServicePopularUsecaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service popular use cases
    """
    
    queryset = ServicePopularUseCase.objects.all()
    serializer_class = ServicePopularUsecaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['service']
    search_fields = ['title', 'description']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on service visibility"""
        if self.request.user.is_staff:
            return ServicePopularUseCase.objects.select_related('service')
        
        # Public users only see use cases from active services
        return ServicePopularUseCase.objects.filter(
            service__active=True
        ).select_related('service')


class ServiceFAQViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing service FAQs
    """
    
    queryset = ServiceFAQ.objects.all()
    serializer_class = ServiceFAQSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service']
    search_fields = ['question', 'answer']
    ordering_fields = ['sort_order', 'id']
    ordering = ['service', 'sort_order']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on service visibility"""
        if self.request.user.is_staff:
            return ServiceFAQ.objects.select_related('service')
        
        # Public users only see FAQs from active services
        return ServiceFAQ.objects.filter(
            service__active=True
        ).select_related('service')


# Simple API views for specific use cases
from rest_framework import generics


class FeaturedServicesAPIView(generics.ListAPIView):
    """
    Get featured services
    """
    
    serializer_class = PublicServiceListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        limit = int(self.request.query_params.get('limit', 6))
        return Service.objects.filter(
            featured=True,
            active=True
        ).prefetch_related('pricing_tiers')[:limit]


class ServicesByCategoryAPIView(generics.ListAPIView):
    """
    Get services by category
    """
    
    serializer_class = PublicServiceListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        category = self.kwargs.get('category')
        return Service.objects.filter(
            category__iexact=category,
            active=True
        ).prefetch_related('pricing_tiers')


class ServiceCategoriesAPIView(generics.ListAPIView):
    """
    Get all service categories with counts
    """
    
    permission_classes = [permissions.AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Return categories with service counts"""
        categories = Service.objects.filter(active=True).values('category').annotate(
            count=Count('id'),
            avg_price=Avg('starting_at')
        ).order_by('category')
        
        return Response({
            'categories': list(categories),
            'total_categories': len(categories)
        })


class ServicePricingModelsAPIView(generics.ListAPIView):
    """
    Get all pricing models with service counts
    """
    
    permission_classes = [permissions.AllowAny]
    
    def list(self, request, *args, **kwargs):
        """Return pricing models with service counts"""
        pricing_models = Service.objects.filter(active=True).values('pricing_model').annotate(
            count=Count('id'),
            avg_price=Avg('starting_at'),
            min_price=Min('starting_at'),
            max_price=Max('starting_at')
        ).order_by('pricing_model')
        
        return Response({
            'pricing_models': list(pricing_models),
            'total_models': len(pricing_models)
        })