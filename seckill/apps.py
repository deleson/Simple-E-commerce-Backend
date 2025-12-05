from django.apps import AppConfig


class SeckillConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seckill'

    def ready(self):
        # 【核心】应用启动时加载信号
        import seckill.signals