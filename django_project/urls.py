"""
URL configuration for django_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path,include
# 1. 引入 spectacular 提供的视图
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


urlpatterns = [
    path('admin/', admin.site.urls),

    # 当访问路径以’api/开头时‘，去’products.urls‘文件里招后续的路标
    path('api/',include('products.urls')),
    path('api/users/', include('users.urls')), # 添加这一行
    path('api/', include('cart.urls')),
    path('api/', include('orders.urls')),

    # 2. 文档相关的路由
    #    - /api/schema/ -> 下载 schema.yaml 文件
    #    - /api/docs/   -> 可交互的 Swagger UI
    #    - /api/redoc/  -> 另一个风格的文档 UI (Redoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),



    path('api/payment/', include('payment.urls')),
    path('api/seller/',  include('sellers.urls')),
    path('api/addresses/', include('addresses.urls')),

    path('api/seckill/', include('seckill.urls')),


]


# 这一段代码必须存在，且缩进正确！
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
