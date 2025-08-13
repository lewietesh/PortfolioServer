from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

class GoogleAuthView(APIView):
    """
    POST /api/v1/accounts/auth/social/google/
    Accepts: { id_token: string }
    If user exists, logs them in. If not, auto-creates and logs in.
    Returns: { access, refresh, user }
    """
    def post(self, request):
        id_token_str = request.data.get('id_token')
        if not id_token_str:
            return Response({'message': 'Missing id_token'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            import os
            audience = os.environ.get('GOOGLE_CLIENT_ID')
            if not audience:
                return Response({'message': 'Google client ID not configured on server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                google_requests.Request(),
                audience=audience
            )
            email = idinfo.get('email')
            if not email:
                return Response({'message': 'No email in Google token'}, status=status.HTTP_400_BAD_REQUEST)
            user, created = User.objects.get_or_create(email=email, defaults={
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'is_active': True,
                'is_verified': True,
            })
            # If user was just created, you may want to set a random password or mark as Google user
            if created:
                user.set_unusable_password()
                user.save()
            # Issue JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_verified': getattr(user, 'is_verified', True),
                }
            })
        except ValueError as e:
            return Response({'message': f'Invalid Google token: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
