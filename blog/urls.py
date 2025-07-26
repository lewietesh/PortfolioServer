# blog/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router for ViewSets
router = DefaultRouter()
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'posts', views.BlogPostViewSet, basename='blogpost')
router.register(r'comments', views.BlogCommentViewSet, basename='blogcomment')

# Define URL patterns
urlpatterns = [
    # Include router URLs (provides full CRUD)
    path('', include(router.urls)),
    
    # Additional simple endpoints
    path('latest/', views.LatestBlogPostsAPIView.as_view(), name='latest-posts'),
    path('posts/<slug:slug>/related/', views.RelatedBlogPostsAPIView.as_view(), name='related-posts'),
]

# The router provides these automatic URLs:

# TAGS:
# GET    /api/v1/blog/tags/                    - List all tags
# POST   /api/v1/blog/tags/                    - Create tag (admin only)
# GET    /api/v1/blog/tags/{slug}/             - Get specific tag
# PUT    /api/v1/blog/tags/{slug}/             - Update tag (admin only)
# PATCH  /api/v1/blog/tags/{slug}/             - Partial update (admin only)
# DELETE /api/v1/blog/tags/{slug}/             - Delete tag (admin only)
# GET    /api/v1/blog/tags/popular/            - Get popular tags

# BLOG POSTS:
# GET    /api/v1/blog/posts/                   - List all posts (public: published only)
# POST   /api/v1/blog/posts/                   - Create post (admin only)
# GET    /api/v1/blog/posts/{slug}/            - Get specific post (increments view count)
# PUT    /api/v1/blog/posts/{slug}/            - Update post (admin only)
# PATCH  /api/v1/blog/posts/{slug}/            - Partial update (admin only)
# DELETE /api/v1/blog/posts/{slug}/            - Delete post (admin only)
# GET    /api/v1/blog/posts/featured/          - Get featured posts
# GET    /api/v1/blog/posts/by_category/       - Get posts by category (?category=tech)
# GET    /api/v1/blog/posts/by_tag/            - Get posts by tag (?tag=django)
# POST   /api/v1/blog/posts/{slug}/publish/    - Publish post (admin only)
# POST   /api/v1/blog/posts/{slug}/unpublish/  - Unpublish post (admin only)
# POST   /api/v1/blog/posts/{slug}/toggle_featured/ - Toggle featured status (admin only)
# GET    /api/v1/blog/posts/stats/             - Get post statistics (admin only)
# POST   /api/v1/blog/posts/{slug}/add_comment/ - Add comment to post (public)

# COMMENTS:
# GET    /api/v1/blog/comments/                - List comments (public: approved only)
# POST   /api/v1/blog/comments/                - Create comment (admin only - use post endpoint instead)
# GET    /api/v1/blog/comments/{id}/           - Get specific comment
# PUT    /api/v1/blog/comments/{id}/           - Update comment (admin only)
# PATCH  /api/v1/blog/comments/{id}/           - Partial update (admin only)
# DELETE /api/v1/blog/comments/{id}/           - Delete comment (admin only)
# POST   /api/v1/blog/comments/{id}/approve/   - Approve comment (admin only)
# POST   /api/v1/blog/comments/{id}/reject/    - Reject comment (admin only)
# GET    /api/v1/blog/comments/pending/        - Get pending comments (admin only)

# ADDITIONAL ENDPOINTS:
# GET    /api/v1/blog/latest/                  - Get latest published posts (?limit=5)
# GET    /api/v1/blog/posts/{slug}/related/    - Get related posts based on tags

# FILTERING & SEARCH EXAMPLES:
# GET /api/v1/blog/posts/?search=django&category=tech&featured=true&ordering=-date_published
# GET /api/v1/blog/posts/?tags__slug=python&author=1&status=published
# GET /api/v1/blog/comments/?blogpost=1&approved=true&ordering=date_created