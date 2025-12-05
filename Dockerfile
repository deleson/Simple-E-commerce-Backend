# 1. 使用官方 Python 基础镜像 (轻量级 Alpine 版本或 Slim 版本)
# 这里推荐 3.11-slim，比 Alpine 兼容性更好（安装 mysqlclient 容易）
FROM python:3.11-slim

# 2. 设置环境变量
# PYTHONDONTWRITEBYTECODE: 不生成 .pyc 文件，减小体积
# PYTHONUNBUFFERED: 保证日志直接输出到终端，方便调试
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. 设置工作目录 (容器内部的文件夹)
WORKDIR /app

# 4. 安装系统级依赖 (为了安装 mysqlclient 和 Pillow)
# 如果是 slim 镜像，需要安装 gcc 等编译工具
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# 5. 复制依赖清单并安装
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 6. 复制项目所有代码到容器
COPY . /app/

# 7. 复制入口脚本并赋予执行权限
COPY entrypoint.sh /app/
# 【关键】修正 Windows 换行符问题 (CRLF -> LF)
# 这一步是为了防止脚本在 Linux 容器里无法执行
RUN sed -i 's/\r$//g' /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 8. 指定容器启动时执行的命令
ENTRYPOINT ["/app/entrypoint.sh"]