from django.contrib import admin
from .models import Order, Testimonial, ContactMessage, Notification, Payment

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'service', 'product', 'status', 'payment_status', 'total_amount', 'date_created')
    list_filter = ('status', 'payment_status', 'currency', 'date_created')
    search_fields = ('id', 'client__email', 'service__name', 'product__name')
    readonly_fields = ('date_created', 'date_updated')
    ordering = ('-date_created',)


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'approved', 'featured', 'rating', 'date_created')
    list_filter = ('approved', 'featured', 'rating')
    search_fields = ('client__email', 'content')
    ordering = ('-date_created',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'subject', 'priority', 'source', 'is_read', 'replied', 'date_created')
    list_filter = ('priority', 'source', 'is_read', 'replied', 'date_created')
    search_fields = ('name', 'email', 'subject', 'message')
    ordering = ('-date_created',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'title', 'priority', 'is_read', 'date_created')
    list_filter = ('type', 'priority', 'is_read')
    search_fields = ('title', 'message', 'user__email')
    ordering = ('-date_created',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'amount', 'currency', 'method', 'status', 'date_created')
    list_filter = ('method', 'status', 'currency')
    search_fields = ('order__id', 'transaction_id', 'order__client__email')
    ordering = ('-date_created',)
