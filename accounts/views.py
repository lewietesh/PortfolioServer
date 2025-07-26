# accounts/views.py
import random
import string
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import User, ClientProfile
from .serializers import (
    UserBasicSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
    UserUpdateSerializer,
    ClientProfileSerializer,
    ClientProfileUpdateSerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
    EmailVerificationSerializer,
    EmailVerificationConfirmSerializer,
)
from .permissions import IsDeveloperOrAdmin, IsOwnerOrReadOnly


@method_decorator(csrf_exempt, name='dispatch')
class AuthViewSet(viewsets.ViewSet):
    """
    Authentication endpoints for registration, login, logout, and verification
    """
    permission_classes = [AllowAny]

    def generate_verification_code(self):
        """Generate 6-digit verification code"""
        return ''.join(random.choices(string.digits, k=6))

    def send_verification_email(self, email, code, purpose):
        """Send verification code via email"""
        subject_map = {
            'email_verification': 'Verify Your Email - Portfolio API',
            'password_reset': 'Password Reset Code - Portfolio API'
        }
        
        message_map = {
            'email_verification': f'Your email verification code is: {code}. This code expires in 10 minutes.',
            'password_reset': f'Your password reset code is: {code}. This code expires in 10 minutes.'
        }
        
        try:
            # Only try to send email if email backend is properly configured
            if hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
                send_mail(
                    subject=subject_map.get(purpose, 'Verification Code'),
                    message=message_map.get(purpose, f'Your verification code is: {code}'),
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portfolio.com'),
                    recipient_list=[email],
                    fail_silently=False,
                )
                return True
            else:
                # Email not configured - log the code for development
                print(f"EMAIL NOT CONFIGURED - Verification code for {email}: {code}")
                return True  # Return True to continue the flow
        except Exception as e:
            print(f"Email sending failed: {e}")
            # Log the code for development/testing
            print(f"DEVELOPMENT - Verification code for {email}: {code}")
            return True  # Return True to continue the flow in development

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new client user
        POST /api/v1/accounts/auth/register/
        """
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            # Create user (inactive until email verified)
            user = serializer.save(is_active=False, role='client')
            
            # Generate and store verification code
            verification_code = self.generate_verification_code()
            cache_key = f"email_verification_{user.email}"
            cache.set(cache_key, verification_code, timeout=600)  # 10 minutes
            
            # Try to send verification email (non-blocking)
            email_sent = self.send_verification_email(user.email, verification_code, 'email_verification')
            
            # Return success response regardless of email status
            response_data = {
                'message': 'Registration successful. Please check your email for verification code.',
                'user_id': str(user.id),
                'email': user.email
            }
            
            # Add development info if email not configured
            if not email_sent or not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                response_data['development_note'] = f'Email not configured. Verification code: {verification_code}'
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def verify_email(self, request):
        """
        Verify email with code
        POST /api/v1/accounts/auth/verify-email/
        """
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']
            
            # Check verification code
            cache_key = f"email_verification_{email}"
            stored_code = cache.get(cache_key)
            
            if stored_code and stored_code == code:
                try:
                    user = User.objects.get(email=email)
                    user.is_active = True
                    user.save()
                    
                    # Clear verification code
                    cache.delete(cache_key)
                    
                    # Generate JWT tokens
                    refresh = RefreshToken.for_user(user)
                    
                    return Response({
                        'message': 'Email verified successfully.',
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                        'user': UserBasicSerializer(user).data
                    }, status=status.HTTP_200_OK)
                
                except User.DoesNotExist:
                    return Response({
                        'error': 'User not found.'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Invalid or expired verification code.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def resend_verification(self, request):
        """
        Resend email verification code
        POST /api/v1/accounts/auth/resend-verification/
        """
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                if user.is_active:
                    return Response({
                        'message': 'Email is already verified.'
                    }, status=status.HTTP_200_OK)
                
                # Generate new verification code
                verification_code = self.generate_verification_code()
                cache_key = f"email_verification_{email}"
                cache.set(cache_key, verification_code, timeout=600)  # 10 minutes
                
                # Try to send verification email (non-blocking)
                email_sent = self.send_verification_email(email, verification_code, 'email_verification')
                
                response_data = {'message': 'Verification code sent successfully.'}
                
                # Add development info if email not configured
                if not email_sent or not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                    response_data['development_note'] = f'Email not configured. Verification code: {verification_code}'
                
                return Response(response_data, status=status.HTTP_200_OK)
            
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found.'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Login user and return JWT tokens
        POST /api/v1/accounts/auth/login/
        """
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if not user.is_active:
                return Response({
                    'error': 'Account is not activated. Please verify your email.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        user = authenticate(request, email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserBasicSerializer(user).data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Logout user by blacklisting refresh token
        POST /api/v1/accounts/auth/logout/
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({
                'message': 'Logout successful.'
            }, status=status.HTTP_200_OK)
        except TokenError:
            return Response({
                'error': 'Invalid token.'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        Refresh JWT access token
        POST /api/v1/accounts/auth/refresh/
        """
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                refresh = RefreshToken(refresh_token)
                return Response({
                    'access': str(refresh.access_token)
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Refresh token is required.'
                }, status=status.HTTP_400_BAD_REQUEST)
        except TokenError:
            return Response({
                'error': 'Invalid or expired refresh token.'
            }, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def forgot_password(self, request):
        """
        Request password reset code
        POST /api/v1/accounts/auth/forgot-password/
        """
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                
                # Generate and store reset code
                reset_code = self.generate_verification_code()
                cache_key = f"password_reset_{email}"
                cache.set(cache_key, reset_code, timeout=600)  # 10 minutes
                
                # Try to send reset email (non-blocking)
                email_sent = self.send_verification_email(email, reset_code, 'password_reset')
                
                response_data = {'message': 'Password reset code sent to your email.'}
                
                # Add development info if email not configured
                if not email_sent or not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                    response_data['development_note'] = f'Email not configured. Reset code: {reset_code}'
                
                return Response(response_data, status=status.HTTP_200_OK)
            
            except User.DoesNotExist:
                # Don't reveal if email exists or not for security
                return Response({
                    'message': 'If the email exists, a reset code has been sent.'
                }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def reset_password(self, request):
        """
        Reset password with verification code
        POST /api/v1/accounts/auth/reset-password/
        """
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']
            new_password = serializer.validated_data['new_password']
            
            # Check reset code
            cache_key = f"password_reset_{email}"
            stored_code = cache.get(cache_key)
            
            if stored_code and stored_code == code:
                try:
                    user = User.objects.get(email=email)
                    user.set_password(new_password)
                    user.save()
                    
                    # Clear reset code
                    cache.delete(cache_key)
                    
                    return Response({
                        'message': 'Password reset successfully.'
                    }, status=status.HTTP_200_OK)
                
                except User.DoesNotExist:
                    return Response({
                        'error': 'User not found.'
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({
                    'error': 'Invalid or expired reset code.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """
    User management ViewSet (admin/developer access only)
    """
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = [IsDeveloperOrAdmin]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserBasicSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserDetailSerializer

    @action(detail=False, methods=['get', 'patch'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get or update current user profile
        GET/PATCH /api/v1/accounts/users/me/
        """
        if request.method == 'GET':
            serializer = UserDetailSerializer(request.user)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        """
        Change user password
        POST /api/v1/accounts/users/change-password/
        """
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({
                'message': 'Password changed successfully.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientProfileViewSet(viewsets.ModelViewSet):
    """
    Client profile management ViewSet
    """
    queryset = ClientProfile.objects.all()
    serializer_class = ClientProfileSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        """Filter queryset based on user role"""
        if self.request.user.role in ['developer', 'admin']:
            return ClientProfile.objects.all()
        elif self.request.user.role == 'client':
            return ClientProfile.objects.filter(user=self.request.user)
        return ClientProfile.objects.none()

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return ClientProfileUpdateSerializer
        return ClientProfileSerializer

    # @action(detail=True, methods=['get'])
    # def projects(self, request, pk=None):
    #     """
    #     Get client's projects
    #     GET /api/v1/accounts/clients/{id}/projects/
    #     """
    #     client_profile = self.get_object()
    #     projects = client_profile.user.client_projects.all()
        
    #     # Import here to avoid circular imports
    #     from projects.serializers import ProjectListSerializer
    #     serializer = ProjectListSerializer(projects, many=True)
    #     return Response(serializer.data)

    # @action(detail=True, methods=['get'])
    # def orders(self, request, pk=None):
    #     """
    #     Get client's orders
    #     GET /api/v1/accounts/clients/{id}/orders/
    #     """
    #     client_profile = self.get_object()
    #     orders = client_profile.user.client_orders.all()
        
    #     # Import here to avoid circular imports
    #     from business.serializers import OrderListSerializer
    #     serializer = OrderListSerializer(orders, many=True)
    #     return Response(serializer.data)