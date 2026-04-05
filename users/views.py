# users/views.py
from rest_framework.response import Response
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from .models import MyUser
from .serializers import (
    UserRegisterSerializer,
    UserSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
)
from .tasks import send_password_reset_email_task
from .services import apply_for_seller

from common.exceptions import BusinessError





# 1. 发送重置邮件
class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = MyUser.objects.get(email=email)

            # 生成 token 和 uid
            # 这里的token区别于jwt
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            # 构造重置链接 (假设前端页面地址是 localhost:8080/reset-password)
            # 这里我们只打印出关键参数，方便测试
            reset_link = f"http://localhost:8080/reset-password?uid={uid}&token={token}"

            # 旧代码: send_mail(...)
            # 新代码: 使用 .delay() 异步调用
            # 注意：传递给 Celery 的参数必须是可序列化的（字符串、数字、列表等），不能传复杂对象（如 user 对象）
            send_password_reset_email_task.delay(
                subject="E电商平台-密码重置",
                message=f"请点击链接进行重置密码: {reset_link}",
                # from_email="admin@example.com",
                recipient_list=[email]
            )



            return Response({"message": "Password reset link sent to email."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 2. 执行重置密码
class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uidb64 = serializer.validated_data['uidb64']
            token = serializer.validated_data['token']
            password = serializer.validated_data['new_password']

            try:
                # 解码用户ID
                uid = force_str(urlsafe_base64_decode(uidb64))
                user = MyUser.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, MyUser.DoesNotExist):
                return Response({"error": "Invalid UID"}, status=status.HTTP_400_BAD_REQUEST)

            # 验证令牌
            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)

            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class UserRegisterView(generics.CreateAPIView):
    """
    一个只用于创建新用户的视图。
    """
    queryset = MyUser.objects.all()
    serializer_class = UserRegisterSerializer


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post (self,request):
        try:
            # 获取前端传来的refresh_token
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            #将其加入黑名单
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)




class UserProfileView(generics.RetrieveAPIView):
    """
    获取当前登录用户的信息
    """
    queryset = MyUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated] #关键，指定该视图需要认证

    def get_object(self):
        # 返回当前请求的用户
        return self.request.user


# 普通用户申请商家
class ApplyForSellerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        shop_name = request.data.get("shop_name")
        shop_description = request.data.get("shop_description", "")

        try:
            apply_for_seller(
                user=user,
                shop_name=shop_name,
                shop_description=shop_description,
            )

            return Response(
                {"message": f'Congratulations! Shop "{shop_name}" created successfully.'},
                status=status.HTTP_201_CREATED,
            )

        except BusinessError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
