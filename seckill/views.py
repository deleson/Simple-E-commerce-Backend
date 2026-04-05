# seckill/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django_redis import get_redis_connection
from .tasks import create_seckill_order_task
from addresses.models import UserAddress

# 引入工具类
from common.utils.address import build_address_snapshot
from common.utils.redis_key import get_seckill_stock_key

class SeckillView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_id):
        user = request.user

        # 0. 简单的参数校验 (实际场景可能需要验证码、限购检查等)
        address_id = request.data.get('address_id')
        if not address_id:
            return Response({"error": "请选择地址"}, status=400)

        # 获取地址快照 (为了传给 Celery)
        try:
            addr = UserAddress.objects.get(id=address_id, user=user)
            address_snapshot = build_address_snapshot(addr)
        except:
            return Response({"error": "地址无效"}, status=400)

        # 1. 连接 Redis
        redis_conn = get_redis_connection("seckill")
        stock_key = get_seckill_stock_key(event_id)


        #         # ================== 第一道防线：用户维度防刷/防重复 ==================
        #         lock_key = f"seckill:{event_id}:user:{user.id}"
        #         # 尝试获取锁，nx=True保证只有一个请求能成功，ex=600设置10分钟过期防死锁
        #         ok = redis_conn.set(lock_key, 1, nx=True, ex=600)
        #         if not ok:
        #             # 如果没拿到锁，说明10分钟内已经点过或者有并发请求，直接打回
        #             return Response({"message": "您请求过于频繁或已参与过该秒杀"}, 400)

        # 2. 【核心】Lua 脚本：原子性判断并扣减库存
        # 返回 1 表示成功，0 表示库存不足
        lua_script = """
            local stock = tonumber(redis.call('get', KEYS[1]))
            if stock and stock > 0 then
                redis.call('decr', KEYS[1])
                return 1
            else
                return 0
            end
        """

        # 执行脚本
        result = redis_conn.eval(lua_script, 1, stock_key)

        if result == 0:
            return Response({"message": "秒杀已结束 (手慢无)"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 秒杀成功 (Redis层) -> 触发异步任务 (MySQL层)
        create_seckill_order_task.delay(user.id, event_id, address_snapshot)

        return Response({"message": "抢购成功！订单正在创建中，请稍后在订单列表中查看。"}, status=status.HTTP_200_OK)