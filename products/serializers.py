from rest_framework import serializers
from .models import ProductSKU,ProductSPU, Category
from django_elasticsearch_dsl_drf.serializers import DocumentSerializer
from .documents import ProductDocument


class ProductDocumentSerializer(DocumentSerializer):
    class Meta:
        # 1. 绑定你的 Document 类
        document = ProductDocument

        # 2. 列出你想返回给前端的字段
        # 注意：这里写的字段，必须在 ProductDocument 中定义过！
        fields = (
            'id',
            'name',
            'description',
            'category',
            'seller',
            'created_at',
        )

# class ProductDocumentSerializer(serializers.Serializer):
#     """
#     专门用于 Elasticsearch 搜索结果的序列化器。
#     因为 ES 返回的数据结构（扁平的）和 数据库模型（嵌套的）不一样。
#     """
#     id = serializers.IntegerField(read_only=True)
#     name = serializers.CharField(read_only=True)
#     description = serializers.CharField(read_only=True)
#
#     # 【关键修正】在 ES 里，category 和 seller 只是存储的字符串名称
#     # 所以这里直接用 CharField，不要用 CategorySerializer
#     category = serializers.CharField(read_only=True)
#     seller = serializers.CharField(read_only=True)
#
#
#     created_at = serializers.DateField(read_only=True)



class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSKUSerializer(serializers.ModelSerializer):
    """用于展示具体的 SKU 信息"""
    spu_name = serializers.CharField(source='spu.name', read_only=True)
    class Meta:
        model = ProductSKU
        fields = ['id', 'spu_name', 'name', 'specifications', 'price', 'stock', 'image']


class ProductSPUSerializer(serializers.ModelSerializer):
    """用于展示 SPU 信息，包含其下的 SKU 列表"""
    category = CategorySerializer(read_only=True)
    seller = serializers.CharField(source='seller.username', read_only=True)
    # 嵌套展示该商品下的所有规格
    skus = ProductSKUSerializer(many=True, read_only=True)

    class Meta:
        model = ProductSPU
        fields = ['id', 'name', 'description', 'category', 'seller', 'created_at', 'skus']


# --- 写入用的 Serializer (用于卖家创建商品) ---

class ProductSKUWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSKU
        fields = ['name', 'specifications', 'price', 'stock', 'image']


class ProductSPUWriteSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    # 允许在创建 SPU 时同时创建多个 SKU
    skus = ProductSKUWriteSerializer(many=True)

    class Meta:
        model = ProductSPU
        fields = ['name', 'description', 'category', 'skus']

    def create(self, validated_data):
        # 这是一个支持嵌套创建的逻辑
        skus_data = validated_data.pop('skus')
        seller = self.context['request'].user

        # 1. 创建 SPU
        spu = ProductSPU.objects.create(seller=seller, **validated_data)

        # 2. 创建关联的 SKU
        for sku_data in skus_data:
            ProductSKU.objects.create(spu=spu, **sku_data)

        return spu