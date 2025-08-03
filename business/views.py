# business/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model

User = get_user_model()


from accounts.permissions import IsDeveloperOrAdmin, IsOwnerOrReadOnly, IsClientOwner
from .models import Order, Testimonial, ContactMessage, Payment, Notification, NewsletterSubscriber
from .serializers import (
    OrderCreateSerializer, OrderListSerializer, OrderDetailSerializer,
    TestimonialCreateSerializer, TestimonialListSerializer,
    ContactMessageSerializer, PaymentSerializer, NotificationSerializer,
    BulkOrderStatusUpdateSerializer, OrderStatsSerializer,
    NewsletterSubscriberSerializer, NewsletterSubscribeSerializer
)
from .utils import (
    generate_order_number, process_payment, create_notification,
    send_contact_notification_email, auto_prioritize_contact_message,
    check_duplicate_contact, get_order_stats, get_dashboard_metrics,
    export_orders_to_csv, validate_order_transition, send_status_update_notification,
    mark_notifications_as_read
)
from .filters import OrderFilter, ContactMessageFilter, TestimonialFilter


class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing orders with comprehensive business logic
    """
    queryset = Order.objects.all().select_related('client', 'service', 'product', 'pricing_tier')
    filterset_class = OrderFilter
    filter_backends = [DjangoFilterBackend]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'list':
            return OrderListSerializer
        elif self.action in ['retrieve', 'update', 'partial_update']:
            return OrderDetailSerializer
        return OrderCreateSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action
        """
        if self.action in ['create', 'list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsDeveloperOrAdmin]
        else:
            permission_classes = [IsDeveloperOrAdmin]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filter queryset based on user role
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return queryset.none()
        
        # Clients can only see their own orders
        if user.role == 'client':
            return queryset.filter(client=user)
        
        # Developers and admins can see all orders
        return queryset
    
    def perform_create(self, serializer):
        """
        Custom order creation logic
        """
        # Auto-assign client if not provided (for client users)
        if self.request.user.role == 'client':
            serializer.save(client=self.request.user)
        else:
            serializer.save()
        
        # Create notification for admins
        order = serializer.instance
        admin_users = self.request.user.__class__.objects.filter(
            role__in=['admin', 'developer']
        )
        
        for admin in admin_users:
            create_notification(
                user=admin,
                notification_type='order',
                title='New Order Received',
                message=f'New order {order.id[:8]} from {order.client.get_full_name()}',
                resource_id=str(order.id),
                resource_type='order',
                priority='medium'
            )
    
    def perform_update(self, serializer):
        """
        Custom order update logic with status transition validation
        """
        old_status = self.get_object().status
        new_status = serializer.validated_data.get('status', old_status)
        
        if old_status != new_status:
            is_valid, message = validate_order_transition(self.get_object(), new_status)
            if not is_valid:
                raise serializers.ValidationError({'status': message})
        
        serializer.save()
        
        # Send notification if status changed
        if old_status != new_status:
            send_status_update_notification(serializer.instance, old_status, new_status)
    
    @action(detail=True, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def mark_paid(self, request, pk=None):
        """
        Mark order as paid and update status
        """
        order = self.get_object()
        
        # Validate payment data
        payment_data = request.data
        required_fields = ['amount', 'method', 'transaction_id']
        
        for field in required_fields:
            if field not in payment_data:
                return Response(
                    {'error': f'{field} is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Process payment
        payment = process_payment(order, payment_data)
        
        if payment:
            return Response({
                'detail': 'Payment processed successfully',
                'payment_id': payment.id,
                'order_status': order.status,
                'payment_status': order.payment_status
            })
        else:
            return Response(
                {'error': 'Failed to process payment'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def refund(self, request, pk=None):
        """
        Process order refund
        """
        order = self.get_object()
        
        if order.payment_status != 'paid':
            return Response(
                {'error': 'Cannot refund unpaid order'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update order status
        old_status = order.status
        order.status = 'refunded'
        order.payment_status = 'refunded'
        order.save()
        
        # Create refund payment record
        Payment.objects.create(
            order=order,
            amount=-order.total_amount,  # Negative amount for refund
            currency=order.currency,
            method='refund',
            transaction_id=f"REFUND-{order.id[:8]}",
            status='paid',
            notes=request.data.get('notes', 'Order refunded')
        )
        
        # Send notification
        send_status_update_notification(order, old_status, 'refunded')
        
        return Response({'detail': 'Order refunded successfully'})
    
    @action(detail=False, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def bulk_update_status(self, request):
        """
        Bulk update order statuses
        """
        serializer = BulkOrderStatusUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            order_ids = serializer.validated_data['order_ids']
            new_status = serializer.validated_data['status']
            notes = serializer.validated_data.get('notes', '')
            
            # Validate all orders exist and transitions are valid
            orders = Order.objects.filter(id__in=order_ids)
            
            if orders.count() != len(order_ids):
                return Response(
                    {'error': 'Some orders not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            invalid_transitions = []
            for order in orders:
                is_valid, message = validate_order_transition(order, new_status)
                if not is_valid:
                    invalid_transitions.append(f"Order {order.id[:8]}: {message}")
            
            if invalid_transitions:
                return Response(
                    {'error': 'Invalid transitions', 'details': invalid_transitions},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update all orders
            updated_count = orders.update(status=new_status)
            
            # Add notes if provided
            if notes:
                for order in orders:
                    order.notes = f"{order.notes}\n{notes}" if order.notes else notes
                    order.save()
            
            return Response({
                'detail': f'Successfully updated {updated_count} orders',
                'updated_orders': list(orders.values_list('id', flat=True))
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsDeveloperOrAdmin])
    def statistics(self, request):
        """
        Get comprehensive order statistics
        """
        # Date filtering
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        
        stats = get_order_stats(date_from, date_to)
        
        serializer = OrderStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsDeveloperOrAdmin])
    def export_csv(self, request):
        """
        Export orders to CSV
        """
        queryset = self.filter_queryset(self.get_queryset())
        csv_data, filename = export_orders_to_csv(queryset)
        
        response = HttpResponse(csv_data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def timeline(self, request, pk=None):
        """
        Get order timeline/history
        """
        order = self.get_object()
        
        # Collect timeline events
        timeline = []
        
        # Order creation
        timeline.append({
            'date': order.date_created,
            'event': 'Order Created',
            'description': f'Order created for {order.client.get_full_name()}',
            'type': 'order'
        })
        
        # Payment events
        for payment in order.payments.all():
            timeline.append({
                'date': payment.date_created,
                'event': f'Payment {payment.status.title()}',
                'description': f'{payment.currency} {payment.amount} via {payment.method}',
                'type': 'payment'
            })
        
        # Sort by date
        timeline.sort(key=lambda x: x['date'], reverse=True)
        
        return Response({'timeline': timeline})


class ContactMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing contact messages
    """
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    filterset_class = ContactMessageFilter
    filter_backends = [DjangoFilterBackend]
    
    def get_permissions(self):
        """
        Allow anyone to create contact messages, restrict other actions
        """
        if self.action == 'create':
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsDeveloperOrAdmin]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Custom contact message creation with validation and notifications
        """
        # Check for duplicates
        email = serializer.validated_data['email']
        phone = serializer.validated_data.get('phone')
        
        if check_duplicate_contact(email, phone):
            # Still create but mark as potential duplicate
            contact = serializer.save()
            contact.notes = "Potential duplicate submission"
            contact.save()
        else:
            contact = serializer.save()
        
        # Auto-prioritize
        priority = auto_prioritize_contact_message(contact)
        contact.priority = priority
        contact.save()
        
        # Send notification email
        send_contact_notification_email(contact)
        
        # Create admin notification
        admin_users = User.objects.filter(role__in=['admin', 'developer'])


        
        for admin in admin_users:
            create_notification(
                user=admin,
                notification_type='contact',
                title='New Contact Message',
                message=f'New message from {contact.name} - {contact.subject}',
                resource_id=str(contact.id),
                resource_type='contact',
                priority=priority
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def mark_read(self, request, pk=None):
        """
        Mark contact message as read
        """
        message = self.get_object()
        message.is_read = True
        message.save()
        
        return Response({'detail': 'Message marked as read'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def mark_replied(self, request, pk=None):
        """
        Mark contact message as replied
        """
        message = self.get_object()
        message.replied = True
        message.is_read = True
        message.save()
        
        return Response({'detail': 'Message marked as replied'})
    
    @action(detail=False, methods=['get'], permission_classes=[IsDeveloperOrAdmin])
    def pending(self, request):
        """
        Get pending contact messages
        """
        pending_messages = self.get_queryset().filter(
            is_read=False,
            replied=False
        ).order_by('-priority', '-date_created')
        
        serializer = self.get_serializer(pending_messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def bulk_mark_read(self, request):
        """
        Bulk mark messages as read
        """
        message_ids = request.data.get('message_ids', [])
        
        if not message_ids:
            return Response(
                {'error': 'message_ids required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_count = self.get_queryset().filter(
            id__in=message_ids
        ).update(is_read=True)
        
        return Response({
            'detail': f'Marked {updated_count} messages as read'
        })


class TestimonialViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing testimonials with approval workflow
    """
    queryset = Testimonial.objects.all().select_related('client', 'project', 'service')
    filterset_class = TestimonialFilter
    filter_backends = [DjangoFilterBackend]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return TestimonialCreateSerializer
        return TestimonialListSerializer
    
    def get_permissions(self):
        """
        Clients can create testimonials, admins manage them
        """
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]  # Public testimonials
        else:
            permission_classes = [IsDeveloperOrAdmin]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filter testimonials based on user and approval status
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        # Public views only see approved testimonials
        if not user.is_authenticated or user.role not in ['admin', 'developer']:
            return queryset.filter(approved=True)
        
        # Clients see their own testimonials
        if user.role == 'client':
            return queryset.filter(client=user)
        
        # Admins see all
        return queryset
    
    def perform_create(self, serializer):
        """
        Auto-assign client for testimonial creation
        """
        if self.request.user.role == 'client':
            serializer.save(client=self.request.user)
        else:
            serializer.save()
        
        # Notify admins of new testimonial
        testimonial = serializer.instance
        admin_users = self.request.user.__class__.objects.filter(
            role__in=['admin', 'developer']
        )
        
        for admin in admin_users:
            create_notification(
                user=admin,
                notification_type='review',
                title='New Testimonial Submitted',
                message=f'New testimonial from {testimonial.client.get_full_name()}',
                resource_id=str(testimonial.id),
                resource_type='testimonial',
                priority='low'
            )
    
    @action(detail=True, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def approve(self, request, pk=None):
        """
        Approve testimonial
        """
        testimonial = self.get_object()
        testimonial.approved = True
        testimonial.save()
        
        return Response({'detail': 'Testimonial approved'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsDeveloperOrAdmin])
    def feature(self, request, pk=None):
        """
        Feature/unfeature testimonial
        """
        testimonial = self.get_object()
        testimonial.featured = not testimonial.featured
        testimonial.save()
        
        action = 'featured' if testimonial.featured else 'unfeatured'
        return Response({'detail': f'Testimonial {action}'})
    
#     @action(detail=False, methods=['get'])
#     def featured(self, request):

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsDeveloperOrAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        return queryset.filter(user=user)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def mark_read(self, request):
        ids = request.data.get('notification_ids')
        updated_count = mark_notifications_as_read(request.user, ids)
        return Response({'detail': f'Marked {updated_count} notifications as read'})

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related('order', 'order__client').all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend]

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsDeveloperOrAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return queryset.none()
        if user.role == 'client':
            return queryset.filter(order__client=user)
        return queryset


class NewsletterSubscriberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing newsletter subscribers
    """
    
    queryset = NewsletterSubscriber.objects.all()
    serializer_class = NewsletterSubscriberSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'source']
    ordering_fields = ['date_subscribed', 'email']
    ordering = ['-date_subscribed']
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['subscribe']:
            return [permissions.AllowAny()]  # Allow public subscription
        return [IsDeveloperOrAdmin()]  # Admin-only for management
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'subscribe':
            return NewsletterSubscribeSerializer
        return NewsletterSubscriberSerializer
    
    @action(detail=False, methods=['post'])
    def subscribe(self, request):
        """
        Public endpoint for newsletter subscription
        """
        serializer = NewsletterSubscribeSerializer(data=request.data)
        if serializer.is_valid():
            subscriber = serializer.save()
            
            # You can add email confirmation logic here
            # send_welcome_email(subscriber.email, subscriber.name)
            
            return Response(
                {
                    'detail': 'Successfully subscribed to newsletter!',
                    'email': subscriber.email,
                    'status': subscriber.status
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def unsubscribe(self, request, pk=None):
        """
        Unsubscribe a user from newsletter
        """
        subscriber = self.get_object()
        subscriber.unsubscribe()
        
        return Response(
            {'detail': f'{subscriber.email} has been unsubscribed.'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def reactivate(self, request, pk=None):
        """
        Reactivate a subscriber
        """
        subscriber = self.get_object()
        subscriber.reactivate()
        
        return Response(
            {'detail': f'{subscriber.email} subscription has been reactivated.'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get newsletter statistics
        """
        total_subscribers = NewsletterSubscriber.objects.count()
        active_subscribers = NewsletterSubscriber.objects.filter(status='active').count()
        unsubscribed = NewsletterSubscriber.objects.filter(status='unsubscribed').count()
        
        return Response({
            'total_subscribers': total_subscribers,
            'active_subscribers': active_subscribers,
            'unsubscribed': unsubscribed,
            'subscription_rate': (active_subscribers / total_subscribers * 100) if total_subscribers > 0 else 0
        })
        
