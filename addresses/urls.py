from rest_framework.routers import DefaultRouter
from .views import UserAddressViewSet


router = DefaultRouter()
router.register(r'',UserAddressViewSet,basename='user-address')


urlpatterns = router.urls
