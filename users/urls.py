from django.urls import path
from .views import UserRegisterView,UserProfileView,ApplyForSellerView,LogoutView,PasswordResetRequestView,PasswordResetConfirmView

# 从simplejwt库种导入视图
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', UserRegisterView.as_view(), name='user-register'),
    path('logout/', LogoutView.as_view(), name='auth_logout'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # 获取Token（登录）
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # 刷新Token
    path('profile/', UserProfileView.as_view(), name='user-profile'),           #用户信息
    path('apply-seller/', ApplyForSellerView.as_view(), name='apply-seller'),       #用户申请商家
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]