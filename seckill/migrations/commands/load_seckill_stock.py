from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
from seckill.models import SeckillEvent


class Command(BaseCommand):
    help = '将所有未结束的秒杀活动库存重置到 Redis'

    def handle(self, *args, **options):
        # 只加载没结束的活动
        now = timezone.now()
        events = SeckillEvent.objects.filter(end_time__gt=now)

        count = 0
        for event in events:
            cache_key = f'seckill_stock_{event.id}'
            cache.set(cache_key, event.seckill_stock, timeout=None)
            self.stdout.write(f"已加载: {event.title} (ID: {event.id}) - 库存: {event.seckill_stock}")
            count += 1

        self.stdout.write(self.style.SUCCESS(f'成功预热 {count} 个秒杀活动的库存！'))