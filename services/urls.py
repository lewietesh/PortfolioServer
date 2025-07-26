# services/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'services', views.ServiceViewSet, basename='service')
router.register(r'pricing-tiers', views.ServicePricingTierViewSet, basename='servicepricingtier')
router.register(r'features', views.ServiceFeatureViewSet, basename='servicefeature')
router.register(r'process-steps', views.ServiceProcessStepViewSet, basename='serviceprocessstep')
router.register(r'deliverables', views.ServiceDeliverableViewSet, basename='servicedeliverable')
router.register(r'tools', views.ServiceToolViewSet, basename='servicetool')
router.register(r'usecases', views.ServicePopularUsecaseViewSet, basename='servicepopularusecase')
router.register(r'faqs', views.ServiceFAQViewSet, basename='servicefaq')

# Define URL patterns
urlpatterns = [
    # Include router URLs (provides full CRUD)
    path('', include(router.urls)),
    
    # Additional simple endpoints
    path('featured/', views.FeaturedServicesAPIView.as_view(), name='featured-services'),
    path('category/<str:category>/', views.ServicesByCategoryAPIView.as_view(), name='services-by-category'),
    path('categories/', views.ServiceCategoriesAPIView.as_view(), name='service-categories'),
    path('pricing-models/', views.ServicePricingModelsAPIView.as_view(), name='pricing-models'),
]

# The router provides these automatic URLs:

# SERVICES:
# GET    /api/v1/services/services/                  - List all services (public: active only, admin: all)
# POST   /api/v1/services/services/                  - Create service (admin only)
# GET    /api/v1/services/services/{slug}/           - Get specific service (public)
# PUT    /api/v1/services/services/{slug}/           - Update service (admin only)
# PATCH  /api/v1/services/services/{slug}/           - Partial update (admin only)
# DELETE /api/v1/services/services/{slug}/           - Delete service (admin only)
# GET    /api/v1/services/services/featured/         - Get featured services (public)
# GET    /api/v1/services/services/by_category/      - Get services by category (?category=web-development)
# GET    /api/v1/services/services/by_pricing_model/ - Get services by pricing model (?pricing_model=fixed)
# GET    /api/v1/services/services/by_price_range/   - Get services by price (?min_price=100&max_price=500)
# POST   /api/v1/services/services/{slug}/toggle_featured/ - Toggle featured status (admin only)
# POST   /api/v1/services/services/{slug}/toggle_active/   - Toggle active status (admin only)
# GET    /api/v1/services/services/stats/            - Get service statistics (admin only)
# GET    /api/v1/services/services/pricing_overview/ - Get pricing overview (public)

# PRICING TIERS:
# GET    /api/v1/services/pricing-tiers/             - List pricing tiers (public: active services only)
# POST   /api/v1/services/pricing-tiers/             - Create pricing tier (admin only)
# GET    /api/v1/services/pricing-tiers/{id}/        - Get specific pricing tier
# PUT    /api/v1/services/pricing-tiers/{id}/        - Update pricing tier (admin only)
# DELETE /api/v1/services/pricing-tiers/{id}/        - Delete pricing tier (admin only)

# FEATURES:
# GET    /api/v1/services/features/                  - List all features (public)
# POST   /api/v1/services/features/                  - Create feature (admin only)
# GET    /api/v1/services/features/{id}/             - Get specific feature
# PUT    /api/v1/services/features/{id}/             - Update feature (admin only)
# DELETE /api/v1/services/features/{id}/             - Delete feature (admin only)

# PROCESS STEPS:
# GET    /api/v1/services/process-steps/             - List process steps (public: active services only)
# POST   /api/v1/services/process-steps/             - Create process step (admin only)
# GET    /api/v1/services/process-steps/{id}/        - Get specific process step
# PUT    /api/v1/services/process-steps/{id}/        - Update process step (admin only)
# DELETE /api/v1/services/process-steps/{id}/        - Delete process step (admin only)

# DELIVERABLES:
# GET    /api/v1/services/deliverables/              - List deliverables (public: active services only)
# POST   /api/v1/services/deliverables/              - Create deliverable (admin only)
# GET    /api/v1/services/deliverables/{id}/         - Get specific deliverable
# PUT    /api/v1/services/deliverables/{id}/         - Update deliverable (admin only)
# DELETE /api/v1/services/deliverables/{id}/         - Delete deliverable (admin only)

# TOOLS:
# GET    /api/v1/services/tools/                     - List tools (public: active services only)
# POST   /api/v1/services/tools/                     - Create tool (admin only)
# GET    /api/v1/services/tools/{id}/                - Get specific tool
# PUT    /api/v1/services/tools/{id}/                - Update tool (admin only)
# DELETE /api/v1/services/tools/{id}/                - Delete tool (admin only)

# USE CASES:
# GET    /api/v1/services/usecases/                  - List use cases (public: active services only)
# POST   /api/v1/services/usecases/                  - Create use case (admin only)
# GET    /api/v1/services/usecases/{id}/             - Get specific use case
# PUT    /api/v1/services/usecases/{id}/             - Update use case (admin only)
# DELETE /api/v1/services/usecases/{id}/             - Delete use case (admin only)

# FAQs:
# GET    /api/v1/services/faqs/                      - List FAQs (public: active services only)
# POST   /api/v1/services/faqs/                      - Create FAQ (admin only)
# GET    /api/v1/services/faqs/{id}/                 - Get specific FAQ
# PUT    /api/v1/services/faqs/{id}/                 - Update FAQ (admin only)
# DELETE /api/v1/services/faqs/{id}/                 - Delete FAQ (admin only)

# ADDITIONAL ENDPOINTS:
# GET    /api/v1/services/featured/                  - Get featured services (public, ?limit=6)
# GET    /api/v1/services/category/{category}/       - Get services by specific category (public)
# GET    /api/v1/services/categories/                - Get all categories with counts (public)
# GET    /api/v1/services/pricing-models/            - Get all pricing models with stats (public)

# FILTERING & SEARCH EXAMPLES:
# GET /api/v1/services/services/?search=website&category=web-development&featured=true&ordering=starting_at
# GET /api/v1/services/services/?pricing_model=fixed&active=true&min_price=100&max_price=500
# GET /api/v1/services/pricing-tiers/?service=1&recommended=true&ordering=price
# GET /api/v1/services/process-steps/?service=1&ordering=step_number
# GET /api/v1/services/faqs/?service=1&search=timeline&ordering=sort_order