#!/bin/sh

# 1. 只有当传入的命令是启动 Web 服务时，才执行迁移和静态文件收集
# 这样防止 Celery Worker 和 Beat 启动时也重复执行这些操作，浪费时间且容易冲突
if [ "$1" = "gunicorn" ]; then
    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    echo "Applying database migrations..."
    python manage.py migrate
fi

# 2. 【核心修正】执行传入的命令
# 这会执行 docker-compose.yml 里定义的 command
echo "Executing command: $@"
exec "$@"