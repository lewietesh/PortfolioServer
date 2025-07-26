# accounts/permissions.py
from rest_framework.permissions import BasePermission


class IsDeveloperOrAdmin(BasePermission):
    """
    Permission to allow access only to developers and admins
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in ['developer', 'admin']
        )


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission to allow users to edit only their own data
    Admins and developers can access all data
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any authenticated user
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Admin and developer can modify anything
        if request.user.role in ['developer', 'admin']:
            return True
        
        # For ClientProfile objects, check if user owns it
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # For User objects, check if it's the same user
        return obj == request.user


class IsClientOwner(BasePermission):
    """
    Permission specifically for client profile access
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin and developer can access all client profiles
        if request.user.role in ['developer', 'admin']:
            return True
        
        # Client can only access their own profile
        if request.user.role == 'client':
            return obj.user == request.user
        
        return False


class IsAccountOwner(BasePermission):
    """
    Permission for account-related operations
    Users can only modify their own account
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Admin and developer can manage any user account
        if request.user.role in ['developer', 'admin']:
            return True
        
        # Users can only access their own account
        return obj == request.user