**本项目是本人作为后端新手初学django所写，仅作为学习使用，并且受限于本人的技术能力，该项目包含的问题和性能问题可能会比较多。**



---

# 🛍️ B2B2C High-Performance E-commerce Backend

> **基于 Django + Docker 的企业级 B2B2C 电商平台后端系统**

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Django](https://img.shields.io/badge/Django-5.0-green) ![Docker](https://img.shields.io/badge/Docker-Compose-2496ED) ![Elasticsearch](https://img.shields.io/badge/Elasticsearch-7.17-yellow) ![Redis](https://img.shields.io/badge/Redis-6.2-red)

## 📖 项目简介

这是一个功能完整、架构先进的 B2B2C 多商户电商后端项目。系统不依赖于简单的 CRUD，而是针对**高并发秒杀**、**实时状态同步**等进行简单的实现，项目采用全栈容器化部署方案（Docker Compose），一键即可拉起包含 Nginx, MySQL, Redis, Elasticsearch, Celery 等 8 个服务。



**简单的网站使用流程如下**：

用户注册后，可以通过浏览商品，然后下单到购物单中，随后支付商品，此时返回支付宝的跳转地址，通过该地址可以跳转到支付宝的支付界面（沙箱模拟），支付成功。

该项目主要涉及方面：登录注册、用户、购物车、订单、评论、商品、卖家、支付记录、地址、秒杀活动



## 🌟 核心特性

### 1. 🏗️ 架构

*   **高并发秒杀系统**：基于 **Redis Lua 脚本** 实现原子扣减，配合 **Celery** 异步削峰，实测单机吞吐量 **500+ RPS** (windows下Waitress运行，locust测试)。
*   **全栈容器化**：使用 Docker Compose 编排 Django, Nginx, MySQL, Redis, ES, Kibana, Celery Worker/Beat。
*   **高性能搜索**：简单集成 **Elasticsearch**，支持商品分词检索、权重排序，并实现 MySQL -> ES 的**异步准实时同步**。
*   **实时消息推送**：基于 **Django Channels (WebSocket)** 实现支付状态毫秒级推送，告别轮询。

###  2.🛒 基本功能

- **用户注册登录：**使用django的jwt进行实现，还实现了用户邮件重置密码功能（需要配置相关邮件设置）

- **基于角色和视图的权限：**通过group和权限类实现用户和商家对不同页面和模型的访问权限区分，简单划分为普通用户和商家，注册成功默认为普通用户，商家需申请（可重叠的角色）

- **商品、购物车、订单、评论的CRUD实现：**对于订单，用户需要有购买记录才可以评论

  

- **对商品的列表查询：**保留了两种，一种使用ES实现，一种使用普通视图实现（但使用django的redis缓存）

- **商品结构模型：**父订单-购物车创建的总订单，保存总价格等；子订单是包含商家信息的具体的订单记录，包含此次购买记录中某商家的所有商品；订单项是子订单下某个具体的商品。

- **支付和退款功能：**接入支付宝沙盒，需要手动配置支付宝公钥和应用私钥等，对于支付直接通过对订单发布post指令获取支付地址，并使用指定的沙盒账号进行支付，接着拆分总订单创建属于不同商家的子订单（沙盒环境不能实现付款拆分），之后在终端中收到支付宝异步回调消息。对于退款，本项目为了简便仅实现对于子订单的退款，即对于某次购物记录的某个商家进行全退款，且并未实现对订单项的退款（逻辑不太合理，需注意）

- **订单超时回收：**在用户下单后，立即减少库存，为了防止恶意占用库存，通过celery设置定时任务，超时则回收（celery beat发送定时任务，celery worker执行，redis实现任务队列）

- **简单实现秒杀功能：**通过Redis缓存秒杀库存，LUA实现库存量的原子操作，并结合celery进行异步调用订单创建（未实现限流等其他功能）

- **商家钱包功能：**记录商家流水收款和退款的记录



### 2. 🛒 业务深度

*   **B2B2C 多商户模型**：支持商家入驻、店铺管理。核心交易链路实现了**“父子订单拆分”**架构。
*   **SPU/SKU 商品体系**：符合行业标准的复杂商品模型，支持多规格管理。
*   **资金结算闭环**：
    *   对接 **支付宝沙箱** 实现真实支付与退款。
    *   内置**卖家钱包系统**，实现订单完成后的自动分账与流水记录。
*   **库存一致性**：采用 **“下单减库存 + 超时自动关单回滚”** 策略，配合数据库行锁与事务机制，确保数据零差错。



---

## 🛠️ 技术栈

| 领域              | 技术选型                | 说明                                   |
| :---------------- | :---------------------- | :------------------------------------- |
| **Web 框架**      | Django 5.x, DRF         | 核心业务逻辑                           |
| **数据库**        | MySQL 8.0               | 数据持久化                             |
| **缓存/消息队列** | Redis 6.2               | 缓存加速、Celery Broker、Channel Layer |
| **搜索引擎**      | Elasticsearch 7.17      | 全文检索                               |
| **异步任务**      | Celery + Celery Beat    | 邮件发送、订单超时取消、异步下单       |
| **实时通讯**      | Django Channels (ASGI)  | WebSocket 支付通知                     |
| **Web 服务器**    | Nginx + Gunicorn        | 反向代理与负载均衡                     |
| **部署**          | Docker & Docker Compose | 全栈容器化编排                         |

---







## 🚀 快速开始 (Quick Start)

第一种是使用原始代码+自行配置env文件

### 1. 环境准备
确保本地已安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)。

### 2. 配置环境变量
在项目根目录下新建 `.env` 文件（可参考 `.env.example`）：

```ini
# .env
DJANGO_SETTINGS_MODULE=django_project.settings
SECRET_KEY=your_secret_key
DEBUG=False

DB_NAME=ecommerce_db
DB_USER=king
DB_PASSWORD=your_password
DB_HOST=db

REDIS_HOST=redis
ES_HOST=elasticsearch

# 支付宝沙箱配置
ALIPAY_APPID=your_appid
# 本地测试可使用 ngrok 地址
PUBLIC_DOMAIN=https://your-ngrok-domain.ngrok-free.dev
```

### 3. 配置密钥
在根目录下创建 `keys/` 文件夹，并放入您的支付宝 RSA2 密钥：
*   `keys/app_private_key.pem`
*   `keys/alipay_public_key.pem`

### 4. 一键启动
```bash
docker-compose up -d --build
```
*首次启动会自动下载镜像并构建，请耐心等待。*

### 5. 初始化数据
系统启动后，数据库是空的，需要进行初始化：

```bash
# 1. 创建超级管理员
docker exec -it ecommerce_backend python manage.py createsuperuser

# 2. 初始化搜索引擎索引
docker exec -it ecommerce_backend python manage.py search_index --rebuild
```

---

## 🌐 访问入口

| 服务               | 地址                       | 说明           |
| :----------------- | :------------------------- | :------------- |
| **Web API / 首页** | http://127.0.0.1/          | Nginx 入口     |
| **Admin 后台**     | http://127.0.0.1/admin/    | 管理员入口     |
| **API 文档**       | http://127.0.0.1/api/docs/ | Swagger UI     |
| **Kibana**         | http://127.0.0.1:5601/     | 数据可视化面板 |

---

## 📂 目录结构

```text
.
├── django_project/      # 项目配置 (Settings, ASGI, WSGI)
├── apps/
│   ├── users/           # 用户与认证
│   ├── products/        # 商品 SPU/SKU 管理 & ES 索引
│   ├── orders/          # 订单核心 (拆单逻辑)
│   ├── cart/            # 购物车
│   ├── payment/         # 支付与 Webhook
│   ├── seckill/         # 秒杀系统 (Redis Lua + Celery)
│   ├── sellers/         # 卖家中心 & 钱包
│   └── ...
├── nginx/               # Nginx 配置文件
├── docker-compose.yml   # 容器编排
├── Dockerfile           # Django 镜像构建
├── requirements.txt     # 依赖清单
├── entrypoint.sh        # 容器启动脚本
└── manage.py
```

---





第二种是直接使用docker镜像+自行配置.env.docker

1. 在项目根目录下新建 `.env.docker` 文件（可参考 `.env.example`）

2. 在根目录下创建 `keys/` 文件夹并配置密钥

3. 在同目录使用指令唤醒的docker（8个服务）

   1. **加载镜像**：

      ```
      docker load -i backend_v1.0.tar
      ```

   2. **启动服务**

      ```
      docker-compose -f docker-compose-2.yml up -d
      ```

      *(此时 Docker 会自动去网上下载 MySQL、Redis 等官方镜像，并使用你本地加载的 my-shop-backend 镜像启动 Django)*。

4. 初始化数据

   系统启动后，数据库是空的，需要进行初始化：

   ```python
   # 1. 创建超级管理员
   docker exec -it ecommerce_backend python manage.py createsuperuser
   
   # 2. 初始化搜索引擎索引
   docker exec -it ecommerce_backend python manage.py search_index --rebuild
   ```



## 