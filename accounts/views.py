from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
# --- Profile management for dashboard ---
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's profile"""
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        """Update current user's profile (partial update)"""
        serializer = UserDetailSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
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
from rest_framework.views import APIView
from social_django.utils import load_strategy, load_backend
from social_core.backends.google import GoogleOAuth2
from django.contrib.auth import login

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
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_later(self, request):
        """
        Allow user to skip email verification (for development or fallback).
        POST /api/v1/accounts/auth/verify-later/
        Requires Authorization header with access token from signup.
        Returns new JWT tokens and user data.
        """
        user = request.user
        if not user or not user.is_authenticated:
            return Response({'message': 'Authentication required.'}, status=status.HTTP_403_FORBIDDEN)
        # Mark user as active, but not verified (could add a verified flag if needed)
        user.is_active = True
        user.save()
        # Optionally clear any pending verification code
        cache_key = f"email_verification_{user.email}"
        cache.delete(cache_key)
        print(f"[VERIFY LATER] User {user.email} skipped verification.")

        # Issue JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        user_data = UserBasicSerializer(user).data
        return Response({
            'success': True,
            'access': access,
            'refresh': str(refresh),
            'user': user_data,
            'message': 'Verification skipped. You can verify your email later from your profile.'
        }, status=status.HTTP_200_OK)
    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Custom login endpoint: checks credentials only.
        POST /api/v1/accounts/auth/login/
        """
        email = request.data.get('email')
        password = request.data.get('password')
        if not email or not password:
            return Response({
                'success': False,
                'message': 'Email and password are required.'
            }, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No account found for this email.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        if not user.check_password(password):
            return Response({
                'success': False,
                'message': 'Incorrect password.'
            }, status=status.HTTP_401_UNAUTHORIZED)
        # Issue JWT tokens
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        user_data = UserBasicSerializer(user).data
        return Response({
            'success': True,
            'access': access,
            'refresh': str(refresh),
            'user': user_data,
            'message': 'Login successful.'
        }, status=status.HTTP_200_OK)
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """
        Refresh JWT access token using refresh token, rotate and blacklist old refresh token.
        POST /api/v1/accounts/auth/refresh/
        """
        from rest_framework_simplejwt.tokens import RefreshToken, TokenError
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Missing refresh token.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            # Blacklist the old refresh token
            try:
                token.blacklist()
            except TokenError:
                pass  # Already blacklisted or not enabled
            # Rotate: issue a new refresh token
            new_refresh = RefreshToken.for_user(token.user)
            access_token = str(new_refresh.access_token)
            return Response({
                'access': access_token,
                'refresh': str(new_refresh)
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid refresh token', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Log out user by blacklisting refresh token (if provided) and returning success.
        POST /api/v1/accounts/auth/logout/
        """
        # Debug: Log incoming Authorization header and user authentication status
        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        print(f"[LOGOUT DEBUG] Authorization header: {auth_header}")
        print(f"[LOGOUT DEBUG] User authenticated: {request.user.is_authenticated}, User: {request.user}")
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception as e:
                return Response({'error': 'Invalid refresh token', 'details': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # Django logout (optional, for session-based auth)
        from django.contrib.auth import logout as django_logout
        django_logout(request)
        return Response({'message': 'Logout successful.'}, status=status.HTTP_200_OK)
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
            try:
                # Create user (inactive until email verified)
                user = serializer.save(is_active=False, role='client')

                # Generate and store verification code
                verification_code = self.generate_verification_code()
                cache_key = f"email_verification_{user.email}"
                cache.set(cache_key, verification_code, timeout=600)  # 10 minutes

                # Try to send verification email (non-blocking)
                email_sent = self.send_verification_email(user.email, verification_code, 'email_verification')

                # Issue JWT tokens for the new user (inactive, but needed for verification)
                from rest_framework_simplejwt.tokens import RefreshToken
                refresh = RefreshToken.for_user(user)
                access = str(refresh.access_token)

                response_data = {
                    'message': 'Registration successful. Please check your email for verification code.',
                    'user_id': str(user.id),
                    'email': user.email,
                    'access': access,
                    'refresh': str(refresh)
                }

                # Add development info if email not configured
                if not email_sent or not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                    response_data['development_note'] = f'Email not configured. Verification code: {verification_code}'

                print(f"[REGISTER] Registration successful for {user.email}. Email sent: {email_sent}")
                return Response(response_data, status=status.HTTP_201_CREATED)
            except Exception as e:
                print(f"[REGISTER ERROR] Exception during registration: {e}")
                return Response({
                    'message': 'Registration failed due to server error',
                    'errors': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Log registration errors for debugging
        print(f"[REGISTER ERROR] Registration failed for {request.data.get('email')}: {serializer.errors}")
        return Response({
            'message': 'Registration failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def verify_email(self, request):
        """
        Verify email with code. Requires Authorization header with access token.
        POST /api/v1/accounts/auth/verify-email/
        """
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            code = serializer.validated_data['code']

            # Check that the user is authenticated and matches the email
            if not request.user.is_authenticated or str(request.user.email).lower() != str(email).lower():
                return Response({'error': 'Access token required and must match email.'}, status=status.HTTP_403_FORBIDDEN)

            # Check verification code
            cache_key = f"email_verification_{email}"
            stored_code = cache.get(cache_key)
            import time
            if stored_code and stored_code == code:
                try:
                    user = User.objects.get(email=email)
                    user.is_active = True
                    user.save()
                    # Clear verification code (single-use)
                    cache.delete(cache_key)
                    # Issue new tokens
                    from rest_framework_simplejwt.tokens import RefreshToken
                    refresh = RefreshToken.for_user(user)
                    access = str(refresh.access_token)
                    print(f"[VERIFY] Email verified for {email} at {int(time.time())}")
                    return Response({
                        'message': 'Email verified successfully.',
                        'user': UserBasicSerializer(user).data,
                        'access': access,
                        'refresh': str(refresh),
                        'errors': {},
                    }, status=status.HTTP_200_OK)
                except User.DoesNotExist:
                    return Response({
                        'message': 'User not found.',
                        'errors': {'user': ['User not found.']}
                    }, status=status.HTTP_404_NOT_FOUND)
            else:
                # Code expiry feedback
                expires_in = cache.ttl(cache_key) if hasattr(cache, 'ttl') else None
                print(f"[VERIFY] Invalid/expired code for {email} at {int(time.time())}")
                return Response({
                    'message': 'Invalid or expired verification code.',
                    'resend_prompt': True,
                    'expires_in': expires_in,
                    'errors': {'code': ['Invalid or expired verification code.']}
                }, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'message': 'Verification failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def resend_verification(self, request):
        """
        Resend email verification code
        POST /api/v1/accounts/auth/resend-verification/
        """
        import time
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            # Rate limiting: allow resend only once every 30 seconds
            rate_key = f"resend_rate_{email}"
            last_sent = cache.get(rate_key)
            now = int(time.time())
            if last_sent and now - last_sent < 30:
                return Response({
                    'message': 'Please wait before resending verification code.',
                    'errors': {'rate_limit': ['Resend allowed once every 30 seconds.']}
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            try:
                user = User.objects.get(email=email)
                if user.is_active:
                    return Response({
                        'message': 'Email is already verified.',
                        'errors': {},
                    }, status=status.HTTP_200_OK)
                # Invalidate old code
                cache_key = f"email_verification_{email}"
                cache.delete(cache_key)
                # Generate new verification code
                verification_code = self.generate_verification_code()
                cache.set(cache_key, verification_code, timeout=600)  # 10 minutes
                # Log resend event
                print(f"[RESEND] Verification code resent for {email} at {now}")
                # Try to send verification email (non-blocking)
                email_sent = self.send_verification_email(email, verification_code, 'email_verification')
                # Mark rate limit
                cache.set(rate_key, now, timeout=30)
                response_data = {
                    'message': 'Verification code sent successfully.',
                    'email_delivery': 'sent' if email_sent else 'logged',
                    'errors': {},
                }
                # Add development info if email not configured
                if not email_sent or not hasattr(settings, 'EMAIL_HOST') or not settings.EMAIL_HOST:
                    response_data['development_note'] = f'Email not configured. Verification code: {verification_code}'
                return Response(response_data, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({
                    'message': 'User not found.',
                    'errors': {'user': ['User not found.']}
                }, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'message': 'Resend failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    # Remove custom login, use dj-rest-auth's built-in login endpoint

    # Remove custom logout, use dj-rest-auth's built-in logout endpoint

    # Remove custom refresh, use dj-rest-auth's built-in token refresh endpoint if needed

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


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        import logging, requests
        logger = logging.getLogger('django')
        access_token = request.data.get('access_token')
        if not access_token:
            return Response({'error': 'Missing access token'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch Google user info using the access token
        google_userinfo_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        resp = requests.get(google_userinfo_url, headers=headers)
        logger.info(f"GoogleAuthView: Google userinfo response: {resp.status_code} {resp.text}")
        if resp.status_code != 200:
            return Response({'error': 'Invalid Google access token'}, status=status.HTTP_400_BAD_REQUEST)
        userinfo = resp.json()

        # Fetch token info to check aud
        tokeninfo_url = 'https://oauth2.googleapis.com/tokeninfo'
        tokeninfo_resp = requests.get(tokeninfo_url, params={'access_token': access_token})
        logger.info(f"GoogleAuthView: Google tokeninfo response: {tokeninfo_resp.status_code} {tokeninfo_resp.text}")
        if tokeninfo_resp.status_code != 200:
            return Response({'error': 'Invalid Google token'}, status=status.HTTP_400_BAD_REQUEST)
        tokeninfo = tokeninfo_resp.json()
        from django.conf import settings
        expected_aud = str(settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY).strip()
        received_aud = str(tokeninfo.get('aud')).strip()
        logger.info(f"GoogleAuthView: Comparing aud values. Expected: '{expected_aud}' (type {type(expected_aud)}), Received: '{received_aud}' (type {type(received_aud)})")
        if received_aud != expected_aud:
            logger.error(f"GoogleAuthView: Token aud mismatch. Expected {expected_aud}, got {received_aud}")
            return Response({'error': 'Google token client ID mismatch'}, status=status.HTTP_400_BAD_REQUEST)

        # Get user details
        email = userinfo.get('email')
        first_name = userinfo.get('given_name', '')
        last_name = userinfo.get('family_name', '')
        picture = userinfo.get('picture', '')

        # Create or get user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, created = User.objects.get_or_create(email=email, defaults={
            'first_name': first_name,
            'last_name': last_name,
            'is_active': True,
        })
        if created:
            logger.info(f"GoogleAuthView: Created new user for email {email}")
        else:
            logger.info(f"GoogleAuthView: Found existing user for email {email}")

        # Optionally update user details
        updated = False
        if user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if user.last_name != last_name:
            user.last_name = last_name
            updated = True
        if updated:
            user.save()

        # Generate JWT token using SimpleJWT
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        logger.info(f"GoogleAuthView: JWT tokens generated: access={str(refresh.access_token)}, refresh={str(refresh)}")
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserBasicSerializer(user).data,
            'message': 'Google login successful.'
        }, status=status.HTTP_200_OK)


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