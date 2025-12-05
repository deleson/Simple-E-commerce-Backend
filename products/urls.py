from django.urls import path, include
from rest_framework_nested import routers
from . import views
from .views import ProductViewSet, ProductDocumentViewSet  # 1. 引入搜索视图
from reviews.views import ReviewViewSet

# --- A. 标准 CRUD 路由 ---
# 创建一个顶级路由器
router = routers.DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

# --- B. 嵌套路由 (Reviews) ---
# 创建一个嵌套路由器
# 第一个是父路由器，第二个是父路由器的前缀，第三个是用于在URL中查找父对象的字段名
products_router = routers.NestedDefaultRouter(router, r'products', lookup='product')
products_router.register(r'reviews', ReviewViewSet, basename='product-reviews')

# --- C. 搜索路由 (Elasticsearch) ---
# 创建一个独立的路由器给搜索用
search_router = routers.DefaultRouter()
# 这里注册的路径也是 'products'，但因为下面我们会挂载到 'search/' 路径下
# 所以最终访问地址是: /api/search/products/
search_router.register(r'products', ProductDocumentViewSet, basename='product-search')

# --- D. URL 汇总 ---
urlpatterns = [
    # 1. 包含 CRUD 路由 (api/products/)
    path('', include(router.urls)),

    # 2. 包含嵌套路由 (api/products/{pk}/reviews/)
    path('', include(products_router.urls)),

    # 3. 包含搜索路由 (api/search/products/)
    path('search/', include(search_router.urls)),

    # 4. 手动定义的 ping
    path('ping/', views.ping),
]