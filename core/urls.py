# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'hero-sections', views.HeroSectionViewSet, basename='herosection')
router.register(r'about-sections', views.AboutSectionViewSet, basename='aboutsection')

# Define URL patterns
urlpatterns = [
    # Include router URLs (provides full CRUD)
    path('', include(router.urls)),
    
    # Alternative simple endpoints (optional - you can choose router or these)
    path('hero/', views.ActiveHeroAPIView.as_view(), name='active-hero'),
    path('about/', views.LatestAboutAPIView.as_view(), name='latest-about'),
]

# The router provides these automatic URLs:
# GET    /api/v1/core/hero-sections/          - List all hero sections (admin only)
# POST   /api/v1/core/hero-sections/          - Create hero section (admin only)
# GET    /api/v1/core/hero-sections/{id}/     - Get specific hero section
# PUT    /api/v1/core/hero-sections/{id}/     - Update hero section (admin only)
# PATCH  /api/v1/core/hero-sections/{id}/     - Partial update (admin only)
# DELETE /api/v1/core/hero-sections/{id}/     - Delete hero section (admin only)
# GET    /api/v1/core/hero-sections/active/   - Get active hero (public)
# POST   /api/v1/core/hero-sections/{id}/activate/ - Activate specific hero (admin only)

# Same pattern for about-sections:
# GET    /api/v1/core/about-sections/         - List all about sections (admin only)
# POST   /api/v1/core/about-sections/         - Create about section (admin only)
# GET    /api/v1/core/about-sections/{id}/    - Get specific about section
# PUT    /api/v1/core/about-sections/{id}/    - Update about section (admin only)
# PATCH  /api/v1/core/about-sections/{id}/    - Partial update (admin only)
# DELETE /api/v1/core/about-sections/{id}/    - Delete about section (admin only)
# GET    /api/v1/core/about-sections/latest/  - Get latest about section (public)

# Simple alternative endpoints:
# GET    /api/v1/core/hero/                   - Get active hero (public)
# GET    /api/v1/core/about/                  - Get latest about (public)