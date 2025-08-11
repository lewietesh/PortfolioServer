# core/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

from .models import HeroSection, AboutSection
from .serializers import (
    HeroSectionSerializer, 
    HeroSectionListSerializer,
    AboutSectionSerializer,
    AboutSectionListSerializer,
    PublicHeroSectionSerializer,
    PublicAboutSectionSerializer
)


class HeroSectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing hero sections
    
    - Admin users can CRUD hero sections
    - Public users can only view active hero section
    - Automatically handles "only one active" business rule
    """
    
    queryset = HeroSection.objects.all()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return HeroSectionListSerializer
        return HeroSectionSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action
        - Public read access for active hero
        - Admin write access for management
        """
        if self.action in ['active_hero', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        if self.request.user.is_staff:
            return HeroSection.objects.all()
        # Public users only see active hero sections
        return HeroSection.objects.filter(is_active=True)
    
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    @method_decorator(vary_on_headers('Authorization'))
    @action(detail=False, methods=['get'], url_path='active')
    def active_hero(self, request):
        """
        Get the currently active hero section for public display
        Cached for performance
        """
        try:
            active_hero = HeroSection.objects.get(is_active=True)
            serializer = PublicHeroSectionSerializer(active_hero)
            return Response(serializer.data)
        except HeroSection.DoesNotExist:
            return Response(
                {'detail': 'No active hero section found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a specific hero section (deactivates others)
        """
        hero = self.get_object()
        
        with transaction.atomic():
            # Deactivate all other hero sections
            HeroSection.objects.filter(is_active=True).update(is_active=False)
            # Activate this one
            hero.is_active = True
            hero.save()
        
        return Response(
            {'detail': f'Hero section "{hero.heading}" is now active.'}, 
            status=status.HTTP_200_OK
        )
    
    def perform_create(self, serializer):
        """
        Handle creation with business logic
        If new hero is set as active, deactivate others
        """
        instance = serializer.save()
        if instance.is_active:
            with transaction.atomic():
                HeroSection.objects.exclude(pk=instance.pk).update(is_active=False)


class AboutSectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing about sections
    
    - Admin users can CRUD about sections
    - Public users can view about content
    """
    
    queryset = AboutSection.objects.all()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return AboutSectionListSerializer
        return AboutSectionSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action
        - Public read access
        - Admin write access
        """
        if self.action in ['list', 'retrieve', 'latest']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
    
    @method_decorator(cache_page(60 * 30))  # Cache for 30 minutes
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get the latest about section for public display
        Cached for performance
        """
        try:
            latest_about = AboutSection.objects.latest('date_created')
            serializer = PublicAboutSectionSerializer(latest_about)
            return Response(serializer.data)
        except AboutSection.DoesNotExist:
            return Response(
                {'detail': 'No about section found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )


# Alternative class-based views for simple cases
from rest_framework import generics
from rest_framework.views import APIView


class ActiveHeroAPIView(generics.RetrieveAPIView):
    """
    Simple API view to get active hero section
    Alternative to ViewSet action for simpler use cases
    """
    
    serializer_class = PublicHeroSectionSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        try:
            return HeroSection.objects.get(is_active=True)
        except HeroSection.DoesNotExist:
            return None
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response(
                {'detail': 'No active hero section found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class LatestAboutAPIView(generics.RetrieveAPIView):
    """
    Simple API view to get latest about section
    Alternative to ViewSet action for simpler use cases
    """
    
    serializer_class = PublicAboutSectionSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_object(self):
        try:
            return AboutSection.objects.latest('date_created')
        except AboutSection.DoesNotExist:
            return None
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response(
                {'detail': 'No about section found.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = self.get_serializer(instance)
        return Response(serializer.data)