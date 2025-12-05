from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    """
    用于“读取”评论的Serializer。
    """
    # 我们不希望暴露用户的完整信息，只显示用户名即可
    user = serializers.ReadOnlyField(source='user.username')
    product = serializers.ReadOnlyField(source='product.name')



    class Meta:
        model = Review
        fields = ['id','user','product','rating','comment','created_at',]

class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    专门用于“创建”评论的Serializer。
    """
    class Meta:
        model = Review
        # 创建时，用户只需要提供评分和内容
        # user和product字段将由视图自动填充，不应由用户输入
        fields = ['rating', 'comment']