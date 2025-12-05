from rest_framework import serializers
from .models import UserAddress
import re

class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id', 'signer_name', 'signer_mobile',
            'province', 'city', 'district', 'address',
            'is_default', 'created_at'
        ]

    def validate_signer_mobile(self,value):
        """
            简单的手机号格式验证
        """
        if not re.match(r'^1[3-9]\d{9}$', value): #以 1 开头、第二位为 3～9，后面跟 9 位数字，共 11 位中国大陆手机号
            raise serializers.ValidationError("手机号码格式不正确")
        return value