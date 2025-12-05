from rest_framework import permissions

class IsSellerUser(permissions.BasePermission):
    """
    自定义权限，只允许属于 'Seller' 组的用户访问。
    """
    def has_permission(self, request, view):
        # 确保用户已登录且属于 'Seller' 组
        return request.user.is_authenticated and request.user.groups.filter(name='Seller').exists()


# users/permissions.py
# ...

class IsCustomerUser(permissions.BasePermission):
    """
    自定义权限，只允许属于 'Customer' 组的用户访问。
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Customer').exists()

# 定义新权限来检查对象所有权
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    自定义权限：
    - 对于读取操作 (GET, HEAD, OPTIONS)，允许任何请求。
    - 对于写入操作 (POST, PUT, PATCH, DELETE)，只允许对象的所有者。
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限允许任何请求,
        # 所以我们总是允许GET, HEAD或OPTIONS请求。
        if request.method in permissions.SAFE_METHODS:
            return True

        # 关键：检查 obj.user 是否等于 request.user
        # 这假设了我们的模型中都有一个名为 'user' 的外键指向用户模型
        # 对于 product，这个字段是 'seller'，所以我们需要特殊处理或创建另一个权限类
        # 让我们先专注于 user 字段
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # 对于 Product 模型，所有者字段是 'seller'
        elif hasattr(obj, 'seller'):
             return obj.seller == request.user

        return False