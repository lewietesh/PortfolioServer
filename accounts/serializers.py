# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, ClientProfile


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic user information for public display
    """
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'role']


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user information for profile management
    """
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 
            'phone', 'role', 'is_active', 'date_joined', 'date_updated'
        ]
        read_only_fields = ['id', 'date_joined', 'date_updated', 'role']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    User registration serializer with password validation
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'phone', 
            'password', 'password_confirm'
        ]
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def validate_email(self, value):
        """Check if email already exists"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value
    
    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    User profile update serializer
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone']
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if value and not value.startswith('+'):
            # Auto-format Kenyan numbers
            if value.startswith('0'):
                value = '+254' + value[1:]
            elif len(value) == 9:
                value = '+254' + value
        return value


class ClientProfileSerializer(serializers.ModelSerializer):
    """
    Client profile serializer with user information
    """
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = ClientProfile
        fields = [
            'user', 'company_name', 'industry', 'account_balance',
            'date_created', 'date_updated'
        ]
        read_only_fields = ['account_balance', 'date_created', 'date_updated']


class ClientProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Client profile update serializer
    """
    class Meta:
        model = ClientProfile
        fields = ['company_name', 'industry']


class PasswordChangeSerializer(serializers.Serializer):
    """
    Password change serializer for authenticated users
    """
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate_current_password(self, value):
        """Validate current password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
    
    def validate(self, attrs):
        """Validate new password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """
    Password reset request serializer
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Normalize email"""
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Password reset confirmation serializer
    """
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)
    
    def validate_code(self, value):
        """Validate verification code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return value
    
    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords don't match.")
        
        # Normalize email
        attrs['email'] = attrs['email'].lower().strip()
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """
    Email verification request serializer
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Normalize email"""
        return value.lower().strip()


class EmailVerificationConfirmSerializer(serializers.Serializer):
    """
    Email verification confirmation serializer
    """
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate_code(self, value):
        """Validate verification code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Code must be 6 digits.")
        return value
    
    def validate_email(self, value):
        """Normalize email"""
        return value.lower().strip()