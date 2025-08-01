from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, ContactMessageViewSet, TestimonialViewSet
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'contacts', ContactMessageViewSet, basename='contactmessage')
router.register(r'testimonials', TestimonialViewSet, basename='testimonial')

urlpatterns = [
    path('', include(router.urls)),
]
