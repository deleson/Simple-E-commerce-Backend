from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seckill', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeckillDeductionRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_id', models.CharField(max_length=64, unique=True, verbose_name='请求ID')),
                ('user_id', models.PositiveIntegerField(verbose_name='用户ID')),
                ('event_id', models.PositiveIntegerField(verbose_name='活动ID')),
                ('status', models.CharField(choices=[('PENDING', '待处理'), ('SUCCESS', '成功'), ('FAILED', '失败'), ('DEAD', '死信')], default='PENDING', max_length=16)),
                ('is_compensated', models.BooleanField(default=False)),
                ('compensate_count', models.PositiveIntegerField(default=0)),
                ('failure_reason', models.CharField(blank=True, default='', max_length=500)),
                ('payload', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': '秒杀扣减流水',
                'verbose_name_plural': '秒杀扣减流水',
            },
        ),
    ]
