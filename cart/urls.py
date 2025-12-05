from rest_framework.routers import DefaultRouter
from .views import CartItemViewSet

router = DefaultRouter()
router.register(r'cart-items', CartItemViewSet, basename='cart-item')

# 这种写法只有router自动生成的urlCRUD
urlpatterns = router.urls