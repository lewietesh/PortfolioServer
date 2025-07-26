# portfolio_api/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# API version prefix
API_VERSION = 'v1'

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),
    
    # API v1 Endpoints
    path(f'api/{API_VERSION}/accounts/', include('accounts.urls')),
    path(f'api/{API_VERSION}/core/', include('core.urls')),
    path(f'api/{API_VERSION}/projects/', include('projects.urls')),
    path(f'api/{API_VERSION}/blog/', include('blog.urls')),
    path(f'api/{API_VERSION}/services/', include('services.urls')),
    path(f'api/{API_VERSION}/products/', include('products.urls')),
    # path(f'api/{API_VERSION}/business/', include('business.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
