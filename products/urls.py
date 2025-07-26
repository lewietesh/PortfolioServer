# products/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'reviews', views.ProductReviewViewSet, basename='productreview')
router.register(r'purchases', views.ProductPurchaseViewSet, basename='productpurchase')
router.register(r'gallery-images', views.ProductGalleryImageViewSet, basename='productgalleryimage')

# Define URL patterns
urlpatterns = [
    # Include router URLs (provides full CRUD)
    path('', include(router.urls)),
    
    # Additional simple endpoints
    path('featured/', views.FeaturedProductsAPIView.as_view(), name='featured-products'),
    path('recent/', views.RecentProductsAPIView.as_view(), name='recent-products'),
    path('categories/', views.ProductCategoriesAPIView.as_view(), name='product-categories'),
    path('types/', views.ProductTypesAPIView.as_view(), name='product-types'),
    path('products/<slug:slug>/related/', views.RelatedProductsAPIView.as_view(), name='related-products'),
]

# The router provides these automatic URLs:

# PRODUCTS:
# GET    /api/v1/products/products/                  - List all products (public: active only, admin: all)
# POST   /api/v1/products/products/                  - Create product (admin only)
# GET    /api/v1/products/products/{slug}/           - Get specific product (public, increments download count)
# PUT    /api/v1/products/products/{slug}/           - Update product (admin only)
# PATCH  /api/v1/products/products/{slug}/           - Partial update (admin only)
# DELETE /api/v1/products/products/{slug}/           - Delete product (admin only)
# GET    /api/v1/products/products/featured/         - Get featured products (public)
# GET    /api/v1/products/products/by_category/      - Get products by category (?category=website-template)
# GET    /api/v1/products/products/by_type/          - Get products by type (?type=template)
# GET    /api/v1/products/products/by_technology/    - Get products by technology (?technology=react)
# GET    /api/v1/products/products/by_price_range/   - Get products by price (?min_price=10&max_price=50)
# POST   /api/v1/products/products/{slug}/toggle_featured/ - Toggle featured status (admin only)
# POST   /api/v1/products/products/{slug}/toggle_active/   - Toggle active status (admin only)
# GET    /api/v1/products/products/{slug}/download/  - Download product (requires purchase for paid items)
# POST   /api/v1/products/products/{slug}/add_review/ - Add review (public)
# GET    /api/v1/products/products/stats/            - Get product statistics (admin only)
# GET    /api/v1/products/products/recent/           - Get recent products (public)
# GET    /api/v1/products/products/top_rated/        - Get top-rated products (public)
# GET    /api/v1/products/products/bestsellers/     - Get best-selling products (public)

# PRODUCT REVIEWS:
# GET    /api/v1/products/reviews/                   - List reviews (public: approved only)
# POST   /api/v1/products/reviews/                   - Create review (admin only - use product endpoint)
# GET    /api/v1/products/reviews/{id}/              - Get specific review
# PUT    /api/v1/products/reviews/{id}/              - Update review (admin only)
# PATCH  /api/v1/products/reviews/{id}/              - Partial update (admin only)
# DELETE /api/v1/products/reviews/{id}/              - Delete review (admin only)
# POST   /api/v1/products/reviews/{id}/approve/      - Approve review (admin only)
# POST   /api/v1/products/reviews/{id}/reject/       - Reject review (admin only)
# GET    /api/v1/products/reviews/pending/           - Get pending reviews (admin only)

# PRODUCT PURCHASES:
# GET    /api/v1/products/purchases/                 - List purchases (auth: own purchases, admin: all)
# POST   /api/v1/products/purchases/                 - Create purchase (admin only)
# GET    /api/v1/products/purchases/{id}/            - Get specific purchase
# PUT    /api/v1/products/purchases/{id}/            - Update purchase (admin only)
# DELETE /api/v1/products/purchases/{id}/            - Delete purchase (admin only)

# GALLERY IMAGES:
# GET    /api/v1/products/gallery-images/            - List gallery images (public: active products only)
# POST   /api/v1/products/gallery-images/            - Create gallery image (admin only)
# GET    /api/v1/products/gallery-images/{id}/       - Get specific gallery image
# PUT    /api/v1/products/gallery-images/{id}/       - Update gallery image (admin only)
# DELETE /api/v1/products/gallery-images/{id}/       - Delete gallery image (admin only)

# ADDITIONAL ENDPOINTS:
# GET    /api/v1/products/featured/                  - Get featured products (public, ?limit=6)
# GET    /api/v1/products/recent/                    - Get recent products (public, ?limit=4)
# GET    /api/v1/products/categories/                - Get all categories with counts (public)
# GET    /api/v1/products/types/                     - Get all product types with counts (public)
# GET    /api/v1/products/products/{slug}/related/   - Get related products (public)

# FILTERING & SEARCH EXAMPLES:
# GET /api/v1/products/products/?search=react&category=website-template&featured=true&ordering=-date_created
# GET /api/v1/products/products/?type=template&price__gte=10&price__lte=50&technologies__name=django
# GET /api/v1/products/reviews/?product=1&rating__gte=4&approved=true&ordering=-date_created
# GET /api/v1/products/purchases/?status=completed&product__category=template&ordering=-date_created
# GET /api/v1/products/gallery-images/?product=1&ordering=sort_order

# BUSINESS LOGIC EXAMPLES:
# Free product download (no authentication required):
# GET /api/v1/products/products/free-template/download/

# Paid product download (requires purchase):
# GET /api/v1/products/products/premium-template/download/
# Headers: Authorization: Bearer <user_token>

# Add product review:
# POST /api/v1/products/products/template-name/add_review/
# Body: {"rating": 5, "review_text": "Great template!"}

# Get products by price range:
# GET /api/v1/products/products/by_price_range/?min_price=0&max_price=25

# Get top-rated products:
# GET /api/v1/products/products/top_rated/?limit=8