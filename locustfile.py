from locust import HttpUser, task, between,constant
import random


class WebsiteUser(HttpUser):
    # 模拟用户在每个任务之间等待 1 到 5 秒（模拟真实人类思考时间）
    # 如果想测极限性能，可以把这个时间改短，或者去掉
    # wait_time = between(1, 3)
    wait_time = constant(0)

    def on_start(self):
        """
        当模拟用户启动时运行。
        我们需要在这里登录，获取 JWT Token。
        """
        # 假设我们用之前创建的卖家账号登录，或者你可以注册一个专门的压测账号
        # 这里为了简单，所有模拟用户都共用一个账号（在读操作压测中没问题）
        # response = self.client.post("/api/users/token/", json={
        #     "username": "Seller_A",  # 刚才生成数据脚本里创建的用户
        #     "password": "RY.?Dn2LhrKA*r:"
        # })
        #
        # if response.status_code == 200:
        #     self.token = response.json()["access"]
        #     self.headers = {"Authorization": f"Bearer {self.token}"}
        # else:
        #     print("登录失败:", response.text)
        #     self.token = None
        #     self.headers = {}

        self.headers= {}

    @task
    def test_ping(self):
        self.client.get("/api/ping/")


    # @task(3)  # 权重3：用户更有可能访问商品列表
    # def view_products_list(self):
    #     """
    #     访问商品列表页
    #     """
    #     self.client.get("/api/products/", headers=self.headers)
    #
    # @task(1)  # 权重1：用户偶尔会点进某个商品看详情
    # def view_product_detail(self):
    #     """
    #     访问商品详情页
    #     """
    #     # 我们假设生成了至少50个商品，随机访问前10个
    #     # 注意：需要根据你数据库实际的 ID 范围调整
    #     product_id = random.randint(20, 200)
    #     self.client.get(f"/api/products/{product_id}/", headers=self.headers)