from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, ContactMessageViewSet, TestimonialViewSet, NewsletterSubscriberViewSet
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'contacts', ContactMessageViewSet, basename='contactmessage')
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')
router.register(r'newsletter', NewsletterSubscriberViewSet, basename='newsletter')

urlpatterns = [
    path('', include(router.urls)),
]
