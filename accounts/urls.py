# accounts/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .google_auth import GoogleAuthView
from .views import UserProfileView

# Create router and register viewsets
router = DefaultRouter()
router.register(r'auth', views.AuthViewSet, basename='auth')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'clients', views.ClientProfileViewSet, basename='client')

# URL patterns

urlpatterns = [
    # Router URLs (includes all ViewSet endpoints)
    path('', include(router.urls)),
    # Google OAuth endpoint
    path('auth/social/google/', GoogleAuthView.as_view()),
    # User profile endpoint for dashboard
    path('users/me/', UserProfileView.as_view(), name='user-profile'),
]

# Complete URL mapping for reference:
"""
Authentication Endpoints:
POST   /api/v1/accounts/auth/register/              # User registration
POST   /api/v1/accounts/auth/verify-email/          # Verify email with code
POST   /api/v1/accounts/auth/resend-verification/   # Resend verification code
POST   /api/v1/accounts/auth/login/                 # User login
POST   /api/v1/accounts/auth/logout/                # User logout
POST   /api/v1/accounts/auth/refresh/               # Refresh JWT token
POST   /api/v1/accounts/auth/forgot-password/       # Request password reset
POST   /api/v1/accounts/auth/reset-password/        # Reset password with code

User Management Endpoints:
GET    /api/v1/accounts/users/                      # List users (admin only)
POST   /api/v1/accounts/users/                      # Create user (admin only)
GET    /api/v1/accounts/users/{id}/                 # Get user details (admin only)
PUT    /api/v1/accounts/users/{id}/                 # Update user (admin only)
PATCH  /api/v1/accounts/users/{id}/                 # Partial update user (admin only)
DELETE /api/v1/accounts/users/{id}/                 # Delete user (admin only)
GET    /api/v1/accounts/users/me/                   # Get current user profile
PATCH  /api/v1/accounts/users/me/                   # Update current user profile
POST   /api/v1/accounts/users/change-password/      # Change password

Client Profile Endpoints:
GET    /api/v1/accounts/clients/                    # List client profiles
GET    /api/v1/accounts/clients/{id}/               # Get client profile
PUT    /api/v1/accounts/clients/{id}/               # Update client profile
PATCH  /api/v1/accounts/clients/{id}/               # Partial update client profile
GET    /api/v1/accounts/clients/{id}/projects/      # Get client's projects
GET    /api/v1/accounts/clients/{id}/orders/        # Get client's orders
"""