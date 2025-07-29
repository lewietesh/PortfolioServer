# projects/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'technologies', views.TechnologyViewSet, basename='technology')
router.register(r'projects', views.ProjectViewSet, basename='project')
router.register(r'comments', views.ProjectCommentViewSet, basename='projectcomment')
router.register(r'gallery-images', views.ProjectGalleryImageViewSet, basename='projectgalleryimage')

# Define URL patterns
urlpatterns = [
    # Include router URLs (provides full CRUD)
    path('', include(router.urls)),
    
    # Additional simple endpoints
    path('featured/', views.FeaturedProjectsAPIView.as_view(), name='featured-projects'),
    path('recent/', views.RecentProjectsAPIView.as_view(), name='recent-projects'),
    path('projects/<slug:slug>/related/', views.RelatedProjectsAPIView.as_view(), name='related-projects'),
]

# The router provides these automatic URLs:

# TECHNOLOGIES:
# GET    /api/v1/projects/technologies/              - List all technologies (public)
# POST   /api/v1/projects/technologies/              - Create technology (admin only)
# GET    /api/v1/projects/technologies/{id}/         - Get specific technology (public)
# PUT    /api/v1/projects/technologies/{id}/         - Update technology (admin only)
# PATCH  /api/v1/projects/technologies/{id}/         - Partial update (admin only)
# DELETE /api/v1/projects/technologies/{id}/         - Delete technology (admin only)
# GET    /api/v1/projects/technologies/by_category/  - Get technologies by category (?category=frontend)
# GET    /api/v1/projects/technologies/popular/      - Get popular technologies (public)


# PROJECTS:
# GET    /api/v1/projects/projects/                  - List projects (public: completed only, admin: all)
# POST   /api/v1/projects/projects/                  - Create project (admin only)
# GET    /api/v1/projects/projects/{slug}/           - Get specific project (public)
# PUT    /api/v1/projects/projects/{slug}/           - Update project (admin only)
# PATCH  /api/v1/projects/projects/{slug}/           - Partial update (admin only)
# DELETE /api/v1/projects/projects/{slug}/           - Delete project (admin only)
# GET    /api/v1/projects/projects/featured/         - Get featured projects (public)
# GET    /api/v1/projects/projects/by_category/      - Get projects by category (?category=web)
# GET    /api/v1/projects/projects/by_technology/    - Get projects by technology (?technology=django)
# GET    /api/v1/projects/projects/by_status/        - Get projects by status (?status=completed)
# POST   /api/v1/projects/projects/{slug}/like/      - Like project (public)
# POST   /api/v1/projects/projects/{slug}/toggle_featured/ - Toggle featured (admin only)
# POST   /api/v1/projects/projects/{slug}/complete/  - Mark as completed (admin only)
# POST   /api/v1/projects/projects/{slug}/add_comment/ - Add comment (public)
# GET    /api/v1/projects/projects/stats/            - Get project statistics (admin only)
# GET    /api/v1/projects/projects/recent/           - Get recent projects (public)

# PROJECT COMMENTS:
# GET    /api/v1/projects/comments/                  - List comments (public: approved only)
# POST   /api/v1/projects/comments/                  - Create comment (admin only - use project endpoint)
# GET    /api/v1/projects/comments/{id}/             - Get specific comment
# PUT    /api/v1/projects/comments/{id}/             - Update comment (admin only)
# PATCH  /api/v1/projects/comments/{id}/             - Partial update (admin only)
# DELETE /api/v1/projects/comments/{id}/             - Delete comment (admin only)
# POST   /api/v1/projects/comments/{id}/approve/     - Approve comment (admin only)
# POST   /api/v1/projects/comments/{id}/reject/      - Reject comment (admin only)
# GET    /api/v1/projects/comments/pending/          - Get pending comments (admin only)

# GALLERY IMAGES:
# GET    /api/v1/projects/gallery-images/            - List gallery images (public)
# POST   /api/v1/projects/gallery-images/            - Create gallery image (admin only)
# GET    /api/v1/projects/gallery-images/{id}/       - Get specific gallery image
# PUT    /api/v1/projects/gallery-images/{id}/       - Update gallery image (admin only)
# DELETE /api/v1/projects/gallery-images/{id}/       - Delete gallery image (admin only)

# ADDITIONAL ENDPOINTS:
# GET    /api/v1/projects/featured/                  - Get featured projects (public, ?limit=6)
# GET    /api/v1/projects/recent/                    - Get recent projects (public, ?limit=4)
# GET    /api/v1/projects/projects/{slug}/related/   - Get related projects (public)

# FILTERING & SEARCH EXAMPLES:
# GET /api/v1/projects/projects/?search=ecommerce&category=web&featured=true&ordering=-date_created
# GET /api/v1/projects/projects/?technologies__name=django&status=completed&client=1
# GET /api/v1/projects/technologies/?category=frontend&search=react&ordering=name
# GET /api/v1/projects/comments/?project=1&approved=true&ordering=date_created
# GET /api/v1/projects/gallery-images/?project=1&ordering=sort_order