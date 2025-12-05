# products/documents.py
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from .models import ProductSPU, Category
from users.models import MyUser

@registry.register_document
class ProductDocument(Document):
    # 定义 ES 里的字段
    # 1. 普通文本字段 (支持分词搜索)
    name = fields.TextField(
        attr='name',
        fields={
            'raw': fields.KeywordField(),  # 保留原始值用于排序或精确过滤
        }
    )
    description = fields.TextField(attr='description')

    # 2. 关联字段 (直接把分类名存进来，方便搜索)
    category = fields.TextField(
        attr='category.name',
        fields={
            'raw': fields.KeywordField(),
        }
    )

    # 3. 关联字段 (卖家用户名)
    seller = fields.TextField(
        attr='seller.username',
        fields={
            'raw': fields.KeywordField(),
        }
    )

    # 4. 数值字段 (创建时间)
    created_at = fields.DateField(attr='created_at')

    class Index:
        # ES 里的索引名字 (相当于数据库表名)
        name = 'products'
        # 这里的设置可以配置分片数等，开发环境默认即可
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }

    class Django:
        model = ProductSPU  # 关联的模型

        # 当这些字段改变时，自动更新 ES 索引
        fields = [
            'id',
        ]
        # # 自动同步：当 Model save/delete 时，自动更新 ES (开发环境推荐 True，生产环境视情况而定)，默认开始同步
        # ignore_signals = False
        # auto_refresh = True

        ignore_signals = True
        auto_refresh = False
        related_models = [Category,MyUser]

    def get_queryset(self):
        # 预加载关联数据，防止构建索引时产生 N+1 问题
        return super().get_queryset().select_related('category', 'seller')

    def get_instances_from_related(self, related_instance):
        """
        当 related_models 里的实例发生变化时，调用此方法。
        我们需要返回受影响的 ProductSPU 列表。
        """
        # 如果变动的是 Category (比如分类改名了)
        if isinstance(related_instance, Category):
            # 返回该分类下的所有商品
            # 注意：这里的 'spus' 是你在 models.py 里定义的 related_name
            return related_instance.spus.all()

            # 如果变动的是 User (比如卖家改名了)
        if isinstance(related_instance, MyUser):
            # 返回该卖家名下的所有商品
            return related_instance.spus.all()




