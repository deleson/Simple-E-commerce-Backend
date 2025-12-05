# payment/urls.py
from django.urls import path
from .views import AlipayWebhookView,payment_success_view

urlpatterns = [
    path('webhook/', AlipayWebhookView.as_view(), name='alipay-webhook'),
    path('success/', payment_success_view, name='payment-success'),
]