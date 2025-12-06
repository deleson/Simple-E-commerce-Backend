#!/bin/sh

# 如果是启动 web 服务
if [ "$1" = "gunicorn" ]; then

    # --- 等待数据库逻辑 (必须有这段) ---
    host="${DB_HOST:-db}"
    port="${DB_PORT:-3306}"

    echo "Check 1: Waiting for MySQL at $host:$port..."

    # 循环检测，直到端口通了为止
    # nc (netcat) 是我们在 Dockerfile 里装的工具
    while ! nc -z $host $port; do
      echo "MySQL is unavailable - sleeping"
      sleep 1
    done

    echo "MySQL is up - continuing"
    # ----------------------------------

    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    echo "Applying database migrations..."
    python manage.py migrate

    echo "Initializing data..."
    # 加上 || true 防止重复初始化报错中断
    python manage.py init_data || true
fi

echo "Executing command: $@"
exec "$@"