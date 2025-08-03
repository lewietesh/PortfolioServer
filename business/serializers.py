# business/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db import models
from decimal import Decimal
import re

from .models import Order, Testimonial, ContactMessage, Payment, Notification, NewsletterSubscriber
from .utils import (
    generate_order_number, calculate_order_total, 
    validate_payment_method, send_order_confirmation_email
)

User = get_user_model()


class ContactMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for contact form submissions with enhanced validation
    """
    
    class Meta:
        model = ContactMessage
        fields = [
            'id', 'name', 'email', 'phone', 'subject', 'message',
            'source', 'is_read', 'replied', 'priority', 'date_created'
        ]
        read_only_fields = ['id', 'is_read', 'replied', 'date_created']
    
    def validate_name(self, value):
        """Validate name field"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Name must be at least 2 characters long.")
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-']+$", value.strip()):
            raise serializers.ValidationError("Name can only contain letters, spaces, hyphens, and apostrophes.")
        
        return value.strip().title()
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if value:
            # Remove all non-digit characters
            cleaned_phone = re.sub(r'\D', '', value)
            
            # Check if it's a valid Kenyan number format
            if cleaned_phone.startswith('254'):
                if len(cleaned_phone) != 12:
                    raise serializers.ValidationError("Invalid Kenyan phone number format.")
            elif cleaned_phone.startswith('0'):
                if len(cleaned_phone) != 10:
                    raise serializers.ValidationError("Invalid phone number format.")
                # Convert to international format
                cleaned_phone = '254' + cleaned_phone[1:]
            else:
                if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
                    raise serializers.ValidationError("Invalid phone number format.")
            
            return '+' + cleaned_phone
        return value
    
    def validate_message(self, value):
        """Validate message content"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        
        if len(value.strip()) > 2000:
            raise serializers.ValidationError("Message cannot exceed 2000 characters.")
        
        return value.strip()
    
    def validate_subject(self, value):
        """Validate subject field"""
        if value and len(value.strip()) > 255:
            raise serializers.ValidationError("Subject cannot exceed 255 characters.")
        return value.strip() if value else ""


class TestimonialCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating testimonials with validation
    """
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    
    class Meta:
        model = Testimonial
        fields = [
            'id', 'client', 'client_name', 'client_email', 'project', 'service',
            'content', 'rating', 'featured', 'approved', 'date_created'
        ]
        read_only_fields = ['id', 'featured', 'approved', 'date_created']
    
    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value is not None:
            if value < 1 or value > 5:
                raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
    
    def validate_content(self, value):
        """Validate testimonial content"""
        if len(value.strip()) < 20:
            raise serializers.ValidationError("Testimonial must be at least 20 characters long.")
        
        if len(value.strip()) > 1000:
            raise serializers.ValidationError("Testimonial cannot exceed 1000 characters.")
        
        return value.strip()
    
    def validate(self, attrs):
        """Cross-field validation"""
        project = attrs.get('project')
        service = attrs.get('service')
        
        # Must be related to either a project or service
        if not project and not service:
            raise serializers.ValidationError(
                "Testimonial must be associated with either a project or service."
            )
        
        return attrs


class TestimonialListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing testimonials with minimal client info
    """
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    project_title = serializers.CharField(source='project.title', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    
    class Meta:
        model = Testimonial
        fields = [
            'id', 'client_name', 'project_title', 'service_name',
            'content', 'rating', 'featured', 'date_created'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payment records with validation
    """
    order_number = serializers.CharField(source='order.id', read_only=True)
    client_name = serializers.CharField(source='order.client.get_full_name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'client_name', 'amount', 'currency',
            'method', 'transaction_id', 'status', 'notes', 'date_created'
        ]
        read_only_fields = ['id', 'date_created']
    
    def validate_amount(self, value):
        """Validate payment amount"""
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0.")
        
        if value > Decimal('1000000.00'):  # 1 million limit
            raise serializers.ValidationError("Payment amount exceeds maximum limit.")
        
        return value
    
    def validate_method(self, value):
        """Validate payment method"""
        return validate_payment_method(value)
    
    def validate_transaction_id(self, value):
        """Validate transaction ID format"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Transaction ID is required and must be at least 3 characters.")
        
        return value.strip().upper()
    
    def validate(self, attrs):
        """Cross-field validation for payments"""
        order = attrs.get('order')
        amount = attrs.get('amount')
        
        if order and amount:
            # Check if payment amount doesn't exceed order total
            if amount > order.total_amount:
                raise serializers.ValidationError(
                    "Payment amount cannot exceed order total."
                )
            
            # Check for duplicate transaction IDs for the same order
            transaction_id = attrs.get('transaction_id')
            if transaction_id:
                existing_payment = Payment.objects.filter(
                    order=order,
                    transaction_id=transaction_id
                ).exclude(id=self.instance.id if self.instance else None).first()
                
                if existing_payment:
                    raise serializers.ValidationError(
                        "Transaction ID already exists for this order."
                    )
        
        return attrs


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating orders with comprehensive validation
    """
    order_number = serializers.CharField(read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    pricing_tier_name = serializers.CharField(source='pricing_tier.name', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'client', 'client_name', 'service', 'service_name',
            'pricing_tier', 'pricing_tier_name', 'product', 'product_name',
            'total_amount', 'currency', 'status', 'payment_status',
            'payment_method', 'transaction_id', 'notes', 'due_date', 'date_created'
        ]
        read_only_fields = ['id', 'date_created']
    
    def validate_total_amount(self, value):
        """Validate order total amount"""
        if value <= 0:
            raise serializers.ValidationError("Order total must be greater than 0.")
        
        if value > Decimal('10000000.00'):  # 10 million limit
            raise serializers.ValidationError("Order total exceeds maximum limit.")
        
        return value
    
    def validate_due_date(self, value):
        """Validate due date is in the future"""
        if value and value <= timezone.now().date():
            raise serializers.ValidationError("Due date must be in the future.")
        return value
    
    def validate(self, attrs):
        """Cross-field validation for orders"""
        service = attrs.get('service')
        product = attrs.get('product')
        pricing_tier = attrs.get('pricing_tier')
        client = attrs.get('client')
        
        # Must have either service or product
        if not service and not product:
            raise serializers.ValidationError(
                "Order must be associated with either a service or product."
            )
        
        # Cannot have both service and product
        if service and product:
            raise serializers.ValidationError(
                "Order cannot be associated with both service and product."
            )
        
        # Validate pricing tier belongs to service
        if pricing_tier and service:
            if pricing_tier.service != service:
                raise serializers.ValidationError(
                    "Pricing tier does not belong to the selected service."
                )
        
        # Validate client role
        if client and client.role != 'client':
            raise serializers.ValidationError(
                "Orders can only be created for client users."
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create order with automatic calculations"""
        # Calculate total if not provided
        if 'total_amount' not in validated_data:
            validated_data['total_amount'] = calculate_order_total(validated_data)
        
        order = super().create(validated_data)
        
        # Send confirmation email
        try:
            send_order_confirmation_email(order)
        except Exception as e:
            # Log error but don't fail order creation
            print(f"Failed to send order confirmation email: {e}")
        
        return order


class OrderListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing orders with essential information
    """
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    pricing_tier_name = serializers.CharField(source='pricing_tier.name', read_only=True)
    payment_count = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'client_name', 'client_email', 'service_name', 'product_name',
            'pricing_tier_name', 'total_amount', 'currency', 'status', 'payment_status',
            'payment_count', 'total_paid', 'due_date', 'date_created'
        ]
    
    def get_payment_count(self, obj):
        """Get number of payments for this order"""
        return obj.payments.filter(status='paid').count()
    
    def get_total_paid(self, obj):
        """Get total amount paid for this order"""
        return obj.payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for individual order view
    """
    client_details = serializers.SerializerMethodField()
    service_details = serializers.SerializerMethodField()
    product_details = serializers.SerializerMethodField()
    pricing_tier_details = serializers.SerializerMethodField()
    payments = PaymentSerializer(many=True, read_only=True)
    payment_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id', 'client_details', 'service_details', 'product_details',
            'pricing_tier_details', 'total_amount', 'currency', 'status',
            'payment_status', 'payment_method', 'transaction_id', 'notes',
            'due_date', 'payments', 'payment_summary', 'date_created', 'date_updated'
        ]
    
    def get_client_details(self, obj):
        """Get client information"""
        if obj.client:
            return {
                'id': obj.client.id,
                'name': obj.client.get_full_name(),
                'email': obj.client.email,
                'phone': obj.client.phone,
            }
        return None
    
    def get_service_details(self, obj):
        """Get service information"""
        if obj.service:
            return {
                'id': obj.service.id,
                'name': obj.service.name,
                'category': obj.service.category,
                'pricing_model': obj.service.pricing_model,
            }
        return None
    
    def get_product_details(self, obj):
        """Get product information"""
        if obj.product:
            return {
                'id': obj.product.id,
                'name': obj.product.name,
                'category': obj.product.category,
                'price': obj.product.price,
            }
        return None
    
    def get_pricing_tier_details(self, obj):
        """Get pricing tier information"""
        if obj.pricing_tier:
            return {
                'id': obj.pricing_tier.id,
                'name': obj.pricing_tier.name,
                'price': obj.pricing_tier.price,
                'currency': obj.pricing_tier.currency,
            }
        return None
    
    def get_payment_summary(self, obj):
        """Get payment summary"""
        payments = obj.payments.all()
        total_paid = payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        return {
            'total_payments': payments.count(),
            'successful_payments': payments.filter(status='paid').count(),
            'failed_payments': payments.filter(status='failed').count(),
            'total_paid': total_paid,
            'balance_due': obj.total_amount - total_paid,
            'payment_status': 'fully_paid' if total_paid >= obj.total_amount else 'partial' if total_paid > 0 else 'unpaid'
        }


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for system notifications
    """
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_name', 'type', 'title', 'subject', 'message',
            'is_read', 'priority', 'resource_id', 'resource_type', 'date_created'
        ]
        read_only_fields = ['id', 'date_created']
    
    def validate_title(self, value):
        """Validate notification title"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Title must be at least 3 characters long.")
        return value.strip()
    
    def validate_message(self, value):
        """Validate notification message"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Message must be at least 5 characters long.")
        return value.strip()


# Bulk operation serializers
class BulkOrderStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for bulk order status updates
    """
    order_ids = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        max_length=50
    )
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_order_ids(self, value):
        """Validate that all order IDs exist"""
        existing_orders = Order.objects.filter(id__in=value).count()
        if existing_orders != len(value):
            raise serializers.ValidationError("Some order IDs do not exist.")
        return value


class OrderStatsSerializer(serializers.Serializer):
    """
    Serializer for order statistics
    """
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    top_services = serializers.ListField()


# Newsletter Serializers
class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    """
    Serializer for newsletter subscribers
    """
    
    class Meta:
        model = NewsletterSubscriber
        fields = [
            'id', 'email', 'name', 'status', 'source', 
            'emails_sent', 'emails_opened', 'last_email_opened',
            'date_subscribed', 'date_unsubscribed'
        ]
        read_only_fields = [
            'id', 'emails_sent', 'emails_opened', 'last_email_opened',
            'date_subscribed', 'date_unsubscribed'
        ]


class NewsletterSubscribeSerializer(serializers.ModelSerializer):
    """
    Serializer for newsletter subscription (public endpoint)
    """
    
    class Meta:
        model = NewsletterSubscriber
        fields = ['email', 'name']
    
    def validate_email(self, value):
        """Validate email and check for duplicates"""
        if not value or not value.strip():
            raise serializers.ValidationError("Email is required.")
        
        email = value.strip().lower()
        
        # Check if already subscribed and active
        existing = NewsletterSubscriber.objects.filter(email=email).first()
        if existing:
            if existing.status == 'active':
                raise serializers.ValidationError("This email is already subscribed to our newsletter.")
            elif existing.status == 'unsubscribed':
                # Reactivate the subscription
                existing.reactivate()
                return email
        
        return email
    
    def validate_name(self, value):
        """Validate name field"""
        if value and value.strip():
            name = value.strip()
            if len(name) < 2:
                raise serializers.ValidationError("Name must be at least 2 characters long.")
            if len(name) > 100:
                raise serializers.ValidationError("Name must be less than 100 characters.")
            return name.title()
        return ""
    
    def create(self, validated_data):
        """Create or reactivate newsletter subscriber"""
        email = validated_data['email'].lower()
        name = validated_data.get('name', '')
        
        # Check if subscriber already exists
        existing = NewsletterSubscriber.objects.filter(email=email).first()
        if existing:
            # Update name and reactivate if necessary
            existing.name = name
            if existing.status != 'active':
                existing.reactivate()
            else:
                existing.save()
            return existing
        
        # Create new subscriber
        return NewsletterSubscriber.objects.create(
            email=email,
            name=name,
            status='active',
            source='website'
        )