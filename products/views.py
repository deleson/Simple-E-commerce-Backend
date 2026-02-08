import logging



from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import viewsets, permissions
from users.permissions import IsSellerUser
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache
# 引入新模型和序列化器
from .models import ProductSPU
from .serializers import ProductSPUSerializer, ProductSPUWriteSerializer, ProductDocumentSerializer

from django_elasticsearch_dsl_drf.constants import LOOKUP_FILTER_TERMS, LOOKUP_FILTER_RANGE
from django_elasticsearch_dsl_drf.filter_backends import (
    FilteringFilterBackend,
    OrderingFilterBackend,
    CompoundSearchFilterBackend,
)
from django_elasticsearch_dsl_drf.viewsets import DocumentViewSet
from .documents import ProductDocument


logger = logging.getLogger(__name__)


class ProductDocumentViewSet(DocumentViewSet):
    """
    基于 Elasticsearch 的商品搜索视图
    """
    document = ProductDocument
    # 这里虽然我们用的是 ES 的 Document，但 DRF 还是需要 Serializer 来渲染结果
    # 注意：直接复用 ModelSerializer 可能会有字段不匹配的问题
    # 但 django-elasticsearch-dsl-drf 足够聪明，通常能处理
    serializer_class = ProductDocumentSerializer

    lookup_field = 'id'

    # 定义后端功能
    filter_backends = [
        CompoundSearchFilterBackend,  # 全文搜索
        FilteringFilterBackend,  # 字段过滤
        OrderingFilterBackend,  # 排序
    ]

    # 1. 定义搜索字段 (q=关键词)
    search_fields = (
        'name',
        'description',
        'category',  # 搜分类名
    )

    # 2. 定义过滤字段 (category=xxx)
    filter_fields = {
        'category': 'category.raw',
        'seller': 'seller.raw',
    }

    # 3. 定义排序字段 (ordering=created_at)
    ordering_fields = {
        'created_at': 'created_at',
    }

    # 默认排序
    ordering = ('-created_at',)



# locust测试用
def ping(request):
    return HttpResponse("pong")


# 定义新权限来检查对象所有权
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限，只允许对象的所有者进行编辑。
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求,
        # 所以我们总是允许GET, HEAD或OPTIONS请求。
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写入权限只授予该商品的所有者 (seller)。
        return obj.seller == request.user




class ProductViewSet(viewsets.ModelViewSet):
    # 现在查询集是 SPU
    # 【优化前】
    #queryset = ProductSPU.objects.all().order_by('-created_at')

    # 【优化后】
    queryset = ProductSPU.objects.all().select_related(
        'category', 'seller'  # 优化一对多外键 (SPU -> Category, SPU -> Seller)
    ).prefetch_related(
        'skus'  # 优化一对多反向查询 (SPU -> 多个 SKUs)
    ).order_by('-created_at')

    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ProductSPUSerializer
        return ProductSPUWriteSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsSellerUser()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsSellerUser(), IsOwnerOrReadOnly()]
        else:
            return [permissions.AllowAny()]

        # --- 1. 缓存读取接口 ---

    @method_decorator(cache_page(60 * 15))  # 缓存 15 分钟
    def list(self, request, *args, **kwargs):
        """
        重写 list 方法，添加缓存装饰器。
        Locust 压测的主要目标就是这个接口。
        """
        logger.debug("[PRODUCT_CACHE][LIST_DB_QUERY] route=products_list")
        return super().list(request, *args, **kwargs)

    @method_decorator(cache_page(60 * 15))
    def retrieve(self, request, *args, **kwargs):
        """
        重写 retrieve 方法，缓存单个商品详情。
        """
        return super().retrieve(request, *args, **kwargs)

    # --- 2. 数据变更时清除缓存 (Cache Invalidation) ---

    # 定义一个清空缓存的辅助函数
    # 注意：cache_page 生成的 key 比较复杂，简单粗暴的做法是直接清空所有缓存，
    # 或者你可以研究更高级的 key 生成策略。这里我们为了演示效果，选择清空整个 default 缓存。
    def _clear_cache(self):
        logger.info("[PRODUCT_CACHE][CLEAR_ALL] reason=product_data_changed")
        cache.clear()

    def perform_create(self, serializer):
        # seller 的设置逻辑已经移到了 Serializer 的 create 方法中
        serializer.save()


