# business/utils.py
import uuid
import re
from decimal import Decimal
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache

from .models import Order, Payment, Notification, ContactMessage, Testimonial
from django.template.loader import render_to_string


def generate_order_number():
    """
    Generate a unique order number with format: ORD-YYYYMMDD-XXXX
    """
    today = datetime.now().strftime('%Y%m%d')
    # Get count of orders created today
    today_orders = Order.objects.filter(
        date_created__date=timezone.now().date()
    ).count()
    
    order_sequence = str(today_orders + 1).zfill(4)
    return f"ORD-{today}-{order_sequence}"


def calculate_order_total(order_data):
    """
    Calculate order total based on service, product, or pricing tier
    """
    service = order_data.get('service')
    product = order_data.get('product')
    pricing_tier = order_data.get('pricing_tier')
    
    if pricing_tier:
        return pricing_tier.price
    elif service:
        return service.starting_at or Decimal('0.00')
    elif product:
        return product.price
    
    return Decimal('0.00')


def validate_payment_method(method):
    """
    Validate and standardize payment method
    """
    valid_methods = {
        'mpesa': 'M-Pesa',
        'card': 'Credit/Debit Card',
        'bank_transfer': 'Bank Transfer',
        'paypal': 'PayPal',
        'stripe': 'Stripe',
        'cash': 'Cash',
        'check': 'Check/Cheque'
    }
    
    method_lower = method.lower().replace(' ', '_').replace('-', '_')
    
    if method_lower in valid_methods:
        return valid_methods[method_lower]
    
    # If not in predefined list, return cleaned version
    return method.strip().title()


def send_order_confirmation_email(order):
    """
    Send order confirmation email to client
    """
    if not order.client.email:
        return False
    
    try:
        subject = f'Order Confirmation - {order.id[:8]}'
        
        context = {
            'order': order,
            'client': order.client,
            'service': order.service,
            'product': order.product,
            'pricing_tier': order.pricing_tier,
            'site_name': 'Your Portfolio',
            'support_email': settings.DEFAULT_FROM_EMAIL,
        }
        
        # Render email template
        html_message = render_to_string('emails/order_confirmation.html', context)
        plain_message = render_to_string('emails/order_confirmation.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.client.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Failed to send order confirmation email: {e}")
        return False


def send_contact_notification_email(contact):
    # Admin Email
    admin_subject = "New Contact Message"
    admin_body = render_to_string("emails/contact_admin_notification.html", {"contact": contact})
    send_mail(
        subject=admin_subject,
        message="",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=["lewismutembei001@gmail.com"],
        html_message=admin_body
    )

    # Auto-response to Sender
    if contact.email:
        user_subject = "Thanks for contacting us!"
        user_body = render_to_string("emails/contact_autoresponse.html", {"contact": contact})
        send_mail(
            subject=user_subject,
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[contact.email],
            html_message=user_body
        )


def create_notification(user, notification_type, title, message, resource_id=None, resource_type=None, priority='medium'):
    """
    Create a system notification
    """
    try:
        notification = Notification.objects.create(
            user=user,
            type=notification_type,
            title=title,
            message=message,
            resource_id=resource_id,
            resource_type=resource_type,
            priority=priority
        )
        return notification
    except Exception as e:
        print(f"Failed to create notification: {e}")
        return None


def process_payment(order, payment_data):
    """
    Process payment for an order
    """
    try:
        # Create payment record
        payment = Payment.objects.create(
            order=order,
            amount=payment_data['amount'],
            currency=payment_data.get('currency', 'KSH'),
            method=validate_payment_method(payment_data['method']),
            transaction_id=payment_data['transaction_id'],
            status='pending',
            notes=payment_data.get('notes', '')
        )
        
        # Update order payment status based on total payments
        total_paid = order.payments.filter(status='paid').aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
        
        if total_paid >= order.total_amount:
            order.payment_status = 'paid'
            order.status = 'confirmed'
        elif total_paid > 0:
            order.payment_status = 'partial'
        
        order.save()
        
        # Create notification for admin
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_users = User.objects.filter(role__in=['admin', 'developer'])
        
        for admin in admin_users:
            create_notification(
                user=admin,
                notification_type='payment',
                title='New Payment Received',
                message=f'Payment of {payment.currency} {payment.amount} received for order {order.id[:8]}',
                resource_id=str(payment.id),
                resource_type='payment',
                priority='medium'
            )
        
        return payment
        
    except Exception as e:
        print(f"Failed to process payment: {e}")
        return None


def get_order_stats(date_from=None, date_to=None):
    """
    Get comprehensive order statistics
    """
    queryset = Order.objects.all()
    
    if date_from:
        queryset = queryset.filter(date_created__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date_created__date__lte=date_to)
    
    # Basic stats
    stats = {
        'total_orders': queryset.count(),
        'pending_orders': queryset.filter(status='pending').count(),
        'confirmed_orders': queryset.filter(status='confirmed').count(),
        'completed_orders': queryset.filter(status='completed').count(),
        'cancelled_orders': queryset.filter(status='cancelled').count(),
    }
    
    # Revenue stats
    revenue_data = queryset.aggregate(
        total_revenue=Sum('total_amount'),
        average_order_value=Avg('total_amount')
    )
    
    stats.update({
        'total_revenue': revenue_data['total_revenue'] or Decimal('0.00'),
        'average_order_value': revenue_data['average_order_value'] or Decimal('0.00'),
    })
    
    # Top services
    top_services = queryset.filter(service__isnull=False).values(
        'service__name'
    ).annotate(
        order_count=Count('id'),
        total_revenue=Sum('total_amount')
    ).order_by('-order_count')[:5]
    
    stats['top_services'] = list(top_services)
    
    # Monthly revenue for the last 12 months
    monthly_revenue = {}
    for i in range(12):
        month_date = timezone.now().replace(day=1) - timedelta(days=30*i)
        month_orders = queryset.filter(
            date_created__year=month_date.year,
            date_created__month=month_date.month
        ).aggregate(total=Sum('total_amount'))
        
        month_key = month_date.strftime('%Y-%m')
        monthly_revenue[month_key] = monthly_revenue['total'] or Decimal('0.00')
    
    stats['monthly_revenue'] = monthly_revenue
    
    return stats


def validate_kenyan_phone(phone_number):
    """
    Validate and format Kenyan phone numbers
    """
    if not phone_number:
        return None
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', phone_number)
    
    # Handle different formats
    if cleaned.startswith('254'):
        if len(cleaned) == 12:
            return f"+{cleaned}"
    elif cleaned.startswith('0'):
        if len(cleaned) == 10:
            return f"+254{cleaned[1:]}"
    elif len(cleaned) == 9:
        return f"+254{cleaned}"
    
    return None


def sanitize_input(text, max_length=None, allow_html=False):
    """
    Sanitize user input for security
    """
    if not text:
        return text
    
    # Strip whitespace
    text = text.strip()
    
    # Remove HTML tags if not allowed
    if not allow_html:
        text = re.sub(r'<[^>]+>', '', text)
    
    # Truncate if max_length specified
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text


def generate_invoice_number(order):
    """
    Generate invoice number for an order
    """
    year = order.date_created.year
    month = order.date_created.month
    
    # Count invoices for the month
    monthly_count = Order.objects.filter(
        date_created__year=year,
        date_created__month=month,
        id__lte=order.id
    ).count()
    
    return f"INV-{year}{month:02d}-{monthly_count:04d}"


def calculate_service_rating(service):
    """
    Calculate average rating for a service based on testimonials
    """
    testimonials = Testimonial.objects.filter(
        service=service,
        approved=True,
        rating__isnull=False
    )
    
    if not testimonials.exists():
        return None
    
    avg_rating = testimonials.aggregate(avg=Avg('rating'))['avg']
    rating_count = testimonials.count()
    
    return {
        'average_rating': round(avg_rating, 1) if avg_rating else None,
        'rating_count': rating_count,
        'ratings_breakdown': {
            '5': testimonials.filter(rating=5).count(),
            '4': testimonials.filter(rating=4).count(),
            '3': testimonials.filter(rating=3).count(),
            '2': testimonials.filter(rating=2).count(),
            '1': testimonials.filter(rating=1).count(),
        }
    }


def get_client_order_history(client, limit=10):
    """
    Get order history for a specific client
    """
    orders = Order.objects.filter(client=client).order_by('-date_created')
    
    if limit:
        orders = orders[:limit]
    
    return orders


def mark_notifications_as_read(user, notification_ids=None):
    """
    Mark notifications as read for a user
    """
    queryset = Notification.objects.filter(user=user, is_read=False)
    
    if notification_ids:
        queryset = queryset.filter(id__in=notification_ids)
    
    return queryset.update(is_read=True)


def get_pending_contact_messages(limit=None):
    """
    Get pending contact messages that need attention
    """
    queryset = ContactMessage.objects.filter(
        is_read=False,
        replied=False
    ).order_by('-date_created', 'priority')
    
    if limit:
        queryset = queryset[:limit]
    
    return queryset


def auto_prioritize_contact_message(contact_message):
    """
    Automatically set priority for contact messages based on content
    """
    high_priority_keywords = [
        'urgent', 'emergency', 'asap', 'immediately', 'critical',
        'bug', 'error', 'broken', 'not working', 'issue'
    ]
    
    medium_priority_keywords = [
        'question', 'help', 'support', 'problem', 'quote',
        'pricing', 'timeline', 'availability'
    ]
    
    message_content = f"{contact_message.subject} {contact_message.message}".lower()
    
    # Check for high priority keywords
    if any(keyword in message_content for keyword in high_priority_keywords):
        return 'high'
    
    # Check for medium priority keywords
    if any(keyword in message_content for keyword in medium_priority_keywords):
        return 'medium'
    
    return 'low'


def check_duplicate_contact(email, phone=None, hours=24):
    """
    Check if contact message is duplicate within specified hours
    """
    time_threshold = timezone.now() - timedelta(hours=hours)
    
    query = Q(email=email, date_created__gte=time_threshold)
    
    if phone:
        query |= Q(phone=phone, date_created__gte=time_threshold)
    
    return ContactMessage.objects.filter(query).exists()


def generate_order_summary_report(start_date, end_date):
    """
    Generate comprehensive order summary report
    """
    orders = Order.objects.filter(
        date_created__date__range=[start_date, end_date]
    )
    
    # Basic metrics
    total_orders = orders.count()
    total_revenue = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    
    # Status breakdown
    status_breakdown = {}
    for status, _ in Order.STATUS_CHOICES:
        status_breakdown[status] = orders.filter(status=status).count()
    
    # Payment status breakdown
    payment_breakdown = {}
    for status, _ in Order.PAYMENT_STATUS_CHOICES:
        payment_breakdown[status] = orders.filter(payment_status=status).count()
    
    # Top clients
    top_clients = orders.values(
        'client__first_name', 'client__last_name', 'client__email'
    ).annotate(
        order_count=Count('id'),
        total_spent=Sum('total_amount')
    ).order_by('-total_spent')[:10]
    
    # Service performance
    service_performance = orders.filter(service__isnull=False).values(
        'service__name', 'service__category'
    ).annotate(
        order_count=Count('id'),
        total_revenue=Sum('total_amount')
    ).order_by('-total_revenue')
    
    # Product performance
    product_performance = orders.filter(product__isnull=False).values(
        'product__name', 'product__category'
    ).annotate(
        order_count=Count('id'),
        total_revenue=Sum('total_amount')
    ).order_by('-total_revenue')
    
    # Average order value by month
    monthly_avg = orders.extra(
        select={'month': "DATE_FORMAT(date_created, '%%Y-%%m')"}
    ).values('month').annotate(
        avg_order_value=Avg('total_amount')
    ).order_by('month')
    
    report = {
        'period': {'start': start_date, 'end': end_date},
        'summary': {
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'average_order_value': total_revenue / total_orders if total_orders > 0 else Decimal('0.00')
        },
        'status_breakdown': status_breakdown,
        'payment_breakdown': payment_breakdown,
        'top_clients': list(top_clients),
        'service_performance': list(service_performance),
        'product_performance': list(product_performance),
        'monthly_averages': list(monthly_avg)
    }
    
    return report


def calculate_client_lifetime_value(client):
    """
    Calculate customer lifetime value
    """
    orders = Order.objects.filter(client=client)
    
    if not orders.exists():
        return {
            'total_orders': 0,
            'total_spent': Decimal('0.00'),
            'average_order_value': Decimal('0.00'),
            'first_order_date': None,
            'last_order_date': None,
            'customer_lifespan_days': 0
        }
    
    total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    total_orders = orders.count()
    first_order = orders.earliest('date_created')
    last_order = orders.latest('date_created')
    
    lifespan_days = (last_order.date_created.date() - first_order.date_created.date()).days
    
    return {
        'total_orders': total_orders,
        'total_spent': total_spent,
        'average_order_value': total_spent / total_orders,
        'first_order_date': first_order.date_created.date(),
        'last_order_date': last_order.date_created.date(),
        'customer_lifespan_days': lifespan_days
    }


def get_order_conversion_funnel():
    """
    Calculate conversion rates through the order process
    """
    # Contact messages (top of funnel)
    total_contacts = ContactMessage.objects.count()
    
    # Orders created (conversion from contact)
    total_orders = Order.objects.count()
    
    # Orders confirmed (conversion from pending)
    confirmed_orders = Order.objects.filter(status='confirmed').count()
    
    # Orders completed (conversion to completion)
    completed_orders = Order.objects.filter(status='completed').count()
    
    # Paid orders
    paid_orders = Order.objects.filter(payment_status='paid').count()
    
    return {
        'contact_to_order_rate': (total_orders / total_contacts * 100) if total_contacts > 0 else 0,
        'order_confirmation_rate': (confirmed_orders / total_orders * 100) if total_orders > 0 else 0,
        'order_completion_rate': (completed_orders / total_orders * 100) if total_orders > 0 else 0,
        'payment_success_rate': (paid_orders / total_orders * 100) if total_orders > 0 else 0,
        'overall_conversion_rate': (completed_orders / total_contacts * 100) if total_contacts > 0 else 0
    }


def cache_order_stats(cache_key='order_stats', timeout=300):
    """
    Cache order statistics for performance
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Calculate and cache the result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return wrapper
    return decorator


@cache_order_stats()
def get_dashboard_metrics():
    """
    Get key metrics for admin dashboard
    """
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's metrics
    today_orders = Order.objects.filter(date_created__date=today)
    today_contacts = ContactMessage.objects.filter(date_created__date=today)
    
    # Week metrics
    week_orders = Order.objects.filter(date_created__date__gte=week_ago)
    week_revenue = week_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    
    # Month metrics
    month_orders = Order.objects.filter(date_created__date__gte=month_ago)
    month_revenue = month_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
    
    # Pending items
    pending_orders = Order.objects.filter(status='pending').count()
    unread_contacts = ContactMessage.objects.filter(is_read=False).count()
    pending_testimonials = Testimonial.objects.filter(approved=False).count()
    
    return {
        'today': {
            'orders': today_orders.count(),
            'contacts': today_contacts.count(),
            'revenue': today_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0.00')
        },
        'week': {
            'orders': week_orders.count(),
            'revenue': week_revenue
        },
        'month': {
            'orders': month_orders.count(),
            'revenue': month_revenue
        },
        'pending': {
            'orders': pending_orders,
            'contacts': unread_contacts,
            'testimonials': pending_testimonials
        }
    }


def export_orders_to_csv(queryset, filename=None):
    """
    Export orders to CSV format
    """
    import csv
    from io import StringIO
    
    if not filename:
        filename = f"orders_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = [
        'Order ID', 'Client Name', 'Client Email', 'Service/Product',
        'Total Amount', 'Currency', 'Status', 'Payment Status',
        'Order Date', 'Due Date'
    ]
    writer.writerow(headers)
    
    # Write data
    for order in queryset:
        service_product = order.service.name if order.service else (
            order.product.name if order.product else 'N/A'
        )
        
        writer.writerow([
            order.id,
            order.client.get_full_name(),
            order.client.email,
            service_product,
            str(order.total_amount),
            order.currency,
            order.get_status_display(),
            order.get_payment_status_display(),
            order.date_created.strftime('%Y-%m-%d %H:%M'),
            order.due_date.strftime('%Y-%m-%d') if order.due_date else 'N/A'
        ])
    
    output.seek(0)
    return output.getvalue(), filename


def validate_order_transition(order, new_status):
    """
    Validate if order status transition is allowed
    """
    current_status = order.status
    
    # Define allowed transitions
    allowed_transitions = {
        'pending': ['confirmed', 'cancelled'],
        'confirmed': ['in_progress', 'cancelled'],
        'in_progress': ['completed', 'cancelled'],
        'completed': ['maintenance'],  # Only for ongoing services
        'cancelled': [],  # Cannot transition from cancelled
        'refunded': []    # Cannot transition from refunded
    }
    
    allowed_next_statuses = allowed_transitions.get(current_status, [])
    
    if new_status not in allowed_next_statuses:
        return False, f"Cannot transition from {current_status} to {new_status}"
    
    return True, "Transition allowed"


def send_status_update_notification(order, old_status, new_status):
    """
    Send notification when order status changes
    """
    try:
        subject = f'Order Status Update - {order.id[:8]}'
        
        context = {
            'order': order,
            'old_status': old_status,
            'new_status': new_status,
            'client': order.client
        }
        
        html_message = render_to_string('emails/status_update.html', context)
        plain_message = render_to_string('emails/status_update.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.client.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        print(f"Failed to send status update notification: {e}")
        return False