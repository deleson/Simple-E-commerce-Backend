from uuid import uuid4

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.utils import timezone
from django_redis import get_redis_connection

from .models import SeckillEvent
from .tasks import create_seckill_order_task
from addresses.models import UserAddress


class SeckillView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_id):
        user = request.user
        address_id = request.data.get('address_id')
        if not address_id:
            return Response({"error": "请选择地址"}, status=400)

        try:
            addr = UserAddress.objects.get(id=address_id, user=user)
            address_snapshot = f"{addr.signer_name} {addr.signer_mobile}..."
        except UserAddress.DoesNotExist:
            return Response({"error": "地址无效"}, status=400)

        try:
            event = SeckillEvent.objects.get(id=event_id)
        except SeckillEvent.DoesNotExist:
            return Response({"error": "活动不存在或已删除"}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        if now < event.start_time or now > event.end_time:
            return Response({"message": "活动未开始或已结束"}, status=status.HTTP_400_BAD_REQUEST)

        redis_conn = get_redis_connection("seckill")
        stock_key = f'seckill_stock_{event_id}'

        lua_script = """
            local stock = tonumber(redis.call('get', KEYS[1]))
            if stock and stock > 0 then
                redis.call('decr', KEYS[1])
                return 1
            else
                return 0
            end
        """

        result = redis_conn.eval(lua_script, 1, stock_key)
        if result == 0:
            return Response({"message": "秒杀已结束 (手慢无)"}, status=status.HTTP_400_BAD_REQUEST)

        request_id = uuid4().hex
        create_seckill_order_task.delay(user.id, event_id, address_snapshot, request_id)

        return Response(
            {
                "message": "抢购成功！订单正在创建中，请稍后在订单列表中查看。",
                "request_id": request_id,
            },
            status=status.HTTP_200_OK,
        )
