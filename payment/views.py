# payment/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse

from common.exceptions import BusinessError
from common.utils.alipay import build_alipay_client
from .services import handle_alipay_payment_callback


def payment_success_view(request):
    # 简单的 http .响应，实际项目中这里应该是一个渲染的前端页面
    return HttpResponse("<h1>支付成功！</h1><p>感谢您的购买，我们正在处理您的订单。</p>")



# 把 Django 的 csrf_exempt 装饰器，应用到类视图（APIView）的 dispatch() 方法上，从而让这个类视图完全跳过 CSRF 校验。

@method_decorator(csrf_exempt, name='dispatch')
class AlipayWebhookView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data.dict()
        signature = data.pop("sign", None)

        alipay = build_alipay_client()
        success = alipay.verify(data, signature)

        if success and data.get("trade_status") in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            order_number = data.get("out_trade_no")

            try:
                handle_alipay_payment_callback(data=data)
            except BusinessError:
                return Response("failure")
            except Exception as e:
                print(f"--- [Webhook Error] 处理订单 {order_number} 时发生未知错误: {e}")
                return Response("failure")

            return Response("success")

        return Response("failure")


