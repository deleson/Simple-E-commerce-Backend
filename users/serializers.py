from rest_framework import serializers
from .models import MyUser
from django.contrib.auth.models import Group

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, label="Confirm password")

    # 由于默认注册是普通用户（买家），所以注释化下面代码
    # role = serializers.CharField(write_only=True,required=True)

    class Meta:
        model = MyUser
        fields = ('username', 'password', 'password2')


    def validate(self, attrs):
        # 校验两次密码是否一致
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):

        # 创建用户实例，并对密码进行哈希加密
        user = MyUser.objects.create_user(
            username=validated_data['username'],
        )
        user.set_password(validated_data['password'])
        user.save()

        # 根据传入的role_name,从数据库中找到对应的Group对象
        try:
            customer_group = Group.objects.get(name__iexact='Customer')
            user.groups.add(customer_group)
        except Group.DoesNotExist:
            # 理论上 validate_role 已经处理了这种情况，但这里作为最后的保险
            # 在生产环境中，这里应该记录一个错误日志
            pass

        return user


# 创建一个新的Serializer，只用于显示用户信息
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ('id', 'username', 'email')

# 1. 请求重置密码 (输入邮箱)
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # 检查邮箱是否存在
        if not MyUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

# 2. 确认重置密码 (输入新密码 + 令牌)
class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    uidb64 = serializers.CharField() # 编码后的用户ID
    token = serializers.CharField()  # 重置令牌

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs