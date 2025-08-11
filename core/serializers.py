# core/serializers.py
from rest_framework import serializers
from .models import HeroSection, AboutSection


class HeroSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for HeroSection model
    Used for homepage hero content management
    """
    
    class Meta:
        model = HeroSection
        fields = [
            'id', 
            'heading', 
            'subheading', 
            'cta_text', 
            'cta_link', 
            'is_active',
            'date_created',
            'date_updated'
        ]
        read_only_fields = ['id', 'date_created', 'date_updated']
    
    def validate_heading(self, value):
        """Ensure heading is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Heading cannot be empty.")
        return value.strip()
    
    def validate_cta_link(self, value):
        """Validate CTA link format if provided"""
        if value and not (value.startswith('http://') or value.startswith('https://') or value.startswith('/')):
            raise serializers.ValidationError("CTA link must be a valid URL or relative path.")
        return value


class HeroSectionListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for hero section lists
    """
    
    class Meta:
        model = HeroSection
        fields = ['id', 'heading', 'is_active', 'date_created']


class AboutSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for AboutSection model
    Used for about page content management
    """
    
    social_links_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AboutSection
        fields = [
            'id',
            'title',
            'description', 
            'media_url',
            'socials_urls',
            'social_links_count',
            'date_created',
            'date_updated'
        ]
        read_only_fields = ['id', 'date_created', 'date_updated', 'social_links_count']
    
    def get_social_links_count(self, obj):
        """Return count of social media links"""
        if obj.socials_urls:
            return len(obj.socials_urls)
        return 0
    
    def validate_title(self, value):
        """Ensure title is not empty"""
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value.strip()
    
    def validate_description(self, value):
        """Ensure description is not empty and has minimum length"""
        if not value.strip():
            raise serializers.ValidationError("Description cannot be empty.")
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Description must be at least 50 characters long.")
        return value.strip()
    
    def validate_media_url(self, value):
        """Validate media URL format if provided"""
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Media URL must be a valid HTTP/HTTPS URL.")
        return value
    
    def validate_socials_urls(self, value):
        """Validate social media URLs structure"""
        if not value:
            return value
        
        if not isinstance(value, list):
            raise serializers.ValidationError("Social URLs must be a list.")
        
        for social in value:
            if not isinstance(social, dict):
                raise serializers.ValidationError("Each social link must be an object with 'name' and 'url' fields.")
            
            if 'name' not in social or 'url' not in social:
                raise serializers.ValidationError("Each social link must have 'name' and 'url' fields.")
            
            if not social['name'].strip():
                raise serializers.ValidationError("Social media name cannot be empty.")
            
            if not social['url'].startswith(('http://', 'https://')):
                raise serializers.ValidationError(f"Social media URL for {social['name']} must be a valid HTTP/HTTPS URL.")
        
        return value


class AboutSectionListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for about section lists
    """
    
    class Meta:
        model = AboutSection
        fields = ['id', 'title', 'date_created']


# Public serializers for frontend consumption
class PublicHeroSectionSerializer(serializers.ModelSerializer):
    """
    Public serializer for active hero section
    Only returns essential fields for frontend
    """
    
    class Meta:
        model = HeroSection
        fields = ['heading', 'subheading', 'cta_text', 'cta_link']


class PublicAboutSectionSerializer(serializers.ModelSerializer):
    """
    Public serializer for about section
    Only returns essential fields for frontend
    """
    
    class Meta:
        model = AboutSection
        fields = ['title', 'description', 'media_url', 'socials_urls']