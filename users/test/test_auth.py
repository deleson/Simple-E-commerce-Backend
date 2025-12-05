import pytest
from django.contrib.auth.models import Group


# 引入获取用户模型的工具
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

# 3. 获取当前激活的用户模型 (这就拿到了你的 users.MyUser)
User = get_user_model()



# @pytest.mark.django_db 是一个“魔法标记”。
# 它告诉 Pytest：“这个测试函数需要访问数据库，请帮我准备一个临时的测试数据库，用完就销毁。”
@pytest.mark.django_db
class TestUserRegistration:

    def setup_method(self):
        """
        每次执行测试方法前，都会自动运行这个 setup 方法。
        我们要在这里准备好“前置数据”。
        """
        # 1. 初始化 API 客户端 (模拟 Postman)
        self.client = APIClient()

        # 2. 注册接口的 URL
        self.url = '/api/users/register/'

        # 3. 【关键】因为是空数据库，我们需要先创建 'Customer' 组
        # 否则注册逻辑里 user.groups.add(...) 可能会找不到组
        self.customer_group = Group.objects.create(name='Customer')

    def test_register_success(self):
        """
        测试用例 1: 输入正确的信息，应该注册成功
        """
        # 准备请求数据
        payload = {
            "username": "new_test_user",
            "password": "complex_password_123",
            "password2": "complex_password_123"
        }

        # 发送 POST 请求 (模拟用户点击注册)
        response = self.client.post(self.url, payload)

        # --- 断言 (Assert) ---
        # 这是测试的核心：判断结果是否符合预期

        # 1. 验证状态码是否为 201 Created
        assert response.status_code == status.HTTP_201_CREATED

        # 2. 验证数据库里是否真的多了一个用户
        assert User.objects.count() == 1

        # 3. 验证这个用户是否真的叫 new_test_user
        new_user = User.objects.get(username="new_test_user")
        assert new_user.username == "new_test_user"

        # 4. 【进阶验证】验证用户是否被自动加入到了 Customer 组
        # 我们的业务逻辑是：注册即买家
        assert new_user.groups.filter(name='Customer').exists()

    def test_register_password_mismatch(self):
        """
        测试用例 2: 两次密码不一致，应该失败
        """
        payload = {
            "username": "fail_user",
            "password": "password_A",
            "password2": "password_B"  # 密码不一致
        }

        response = self.client.post(self.url, payload)

        # 断言状态码应该是 400 Bad Request
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 验证数据库里应该没有用户被创建
        assert User.objects.count() == 0