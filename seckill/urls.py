from django.urls import path
from .views import SeckillView

urlpatterns = [
    path('<int:event_id>/buy/', SeckillView.as_view(), name='seckill-buy'),
]