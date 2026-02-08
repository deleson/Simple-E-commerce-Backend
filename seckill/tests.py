from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from orders.models import Order
from products.models import Category, ProductSPU, ProductSKU
from seckill.models import SeckillEvent, SeckillDeductionRecord
from seckill.tasks import create_seckill_order_task


class FakeRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value):
        self.data[key] = int(value)

    def get(self, key):
        return self.data.get(key)

    def eval(self, script, numkeys, key, *args):
        if 'decr' in script:
            stock = self.data.get(key, 0)
            if stock > 0:
                self.data[key] = stock - 1
                return 1
            return 0

        if 'incr' in script:
            max_stock = int(args[0])
            current = int(self.data.get(key, 0))
            if current >= max_stock:
                return current
            current += 1
            if current > max_stock:
                current = max_stock
            self.data[key] = current
            return current

        raise AssertionError('unexpected lua script')


class SeckillCompensationTests(TestCase):
    def setUp(self):
        self.redis = FakeRedis()
        self.redis_patcher_signals = patch('seckill.signals.get_redis_connection', return_value=self.redis)
        self.redis_patcher_tasks = patch('seckill.tasks.get_redis_connection', return_value=self.redis)
        self.redis_patcher_signals.start()
        self.redis_patcher_tasks.start()

        user_model = get_user_model()
        self.buyer = user_model.objects.create_user(username='buyer', password='x')
        self.seller = user_model.objects.create_user(username='seller', password='x')

        category = Category.objects.create(name='c1')
        spu = ProductSPU.objects.create(name='spu1', description='d', category=category, seller=self.seller)
        self.sku = ProductSKU.objects.create(spu=spu, name='sku1', specifications={}, price=Decimal('99.00'), stock=20)

        self.event = SeckillEvent.objects.create(
            sku=self.sku,
            title='flash',
            seckill_stock=5,
            start_time=timezone.now() - timedelta(minutes=10),
            end_time=timezone.now() + timedelta(minutes=10),
        )
        self.redis.set(f'seckill_stock_{self.event.id}', 4)

    def tearDown(self):
        self.redis_patcher_signals.stop()
        self.redis_patcher_tasks.stop()

    def test_task_success_sets_success_status(self):
        result = create_seckill_order_task.run(
            self.buyer.id,
            self.event.id,
            'addr',
            'req-success-1',
        )

        self.assertIn('Seckill Order Created', result)
        self.assertEqual(Order.objects.count(), 2)

        record = SeckillDeductionRecord.objects.get(request_id='req-success-1')
        self.assertEqual(record.status, SeckillDeductionRecord.Status.SUCCESS)
        self.assertFalse(record.is_compensated)
        self.assertEqual(self.redis.get(f'seckill_stock_{self.event.id}'), 4)

    @patch('orders.models.Order.objects.create', side_effect=RuntimeError('db write failed'))
    def test_task_failure_compensates_stock(self, _mock_create):
        with patch.object(create_seckill_order_task, 'retry', side_effect=RuntimeError('retry called')):
            with self.assertRaises(RuntimeError):
                create_seckill_order_task.run(
                    self.buyer.id,
                    self.event.id,
                    'addr',
                    'req-fail-1',
                )

        record = SeckillDeductionRecord.objects.get(request_id='req-fail-1')
        self.assertTrue(record.is_compensated)
        self.assertEqual(record.compensate_count, 1)
        self.assertIn('recoverable_error', record.failure_reason)
        self.assertEqual(self.redis.get(f'seckill_stock_{self.event.id}'), 5)

    @patch('orders.models.Order.objects.create', side_effect=RuntimeError('db write failed again'))
    def test_repeat_retry_will_not_over_compensate(self, _mock_create):
        with patch.object(create_seckill_order_task, 'retry', side_effect=RuntimeError('retry called')):
            for _ in range(2):
                with self.assertRaises(RuntimeError):
                    create_seckill_order_task.run(
                        self.buyer.id,
                        self.event.id,
                        'addr',
                        'req-repeat-1',
                    )

        record = SeckillDeductionRecord.objects.get(request_id='req-repeat-1')
        self.assertTrue(record.is_compensated)
        self.assertEqual(record.compensate_count, 1)
        self.assertEqual(self.redis.get(f'seckill_stock_{self.event.id}'), 5)
