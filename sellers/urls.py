from django.urls import path
from .views import SellerProfileView, SellerOrderListView, SellerOrderDetailView, SellerWalletView, \
    SellerTransactionListView

urlpatterns = [
    path('profile/', SellerProfileView.as_view(), name='seller-profile'),
    path('orders/', SellerOrderListView.as_view(), name='seller-orders'),
    path('orders/<uuid:order_number>/', SellerOrderDetailView.as_view(), name='seller-order-detail'), #商家对单个订单操作
    path('wallet/', SellerWalletView.as_view(), name='seller-wallet'),
    path('wallet/transactions/', SellerTransactionListView.as_view(), name='seller-transactions'),
]