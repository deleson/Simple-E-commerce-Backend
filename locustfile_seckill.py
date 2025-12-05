from locust import HttpUser, task, between, events

# 全局变量存储 Token
SHARED_TOKEN = None
SHARED_HEADERS = {}


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """
    测试开始前，只执行一次登录
    """
    global SHARED_TOKEN, SHARED_HEADERS
    print("--- [Locust] 正在执行全局登录... ---")

    # 这里的 UserClient 是临时的，只为了发登录请求
    # 注意：这里我们手动构造一个请求
    import requests
    base_url = environment.host

    try:
        response = requests.post(f"{base_url}/api/users/token/", json={
            "username": "final_customer",
            "password": "some_password"
        })
        if response.status_code == 200:
            SHARED_TOKEN = response.json()["access"]
            SHARED_HEADERS = {"Authorization": f"Bearer {SHARED_TOKEN}"}
            print(f"--- [Locust] 登录成功，Token 已获取 ---")
        else:
            print(f"--- [Locust] 登录失败: {response.text} ---")
    except Exception as e:
        print(f"--- [Locust] 登录异常: {e} ---")


class SeckillUser(HttpUser):
    # 极速模式，无等待
    wait_time = between(0.01, 0.1)

    # 请根据实际情况修改 ID
    EVENT_ID = 2
    ADDRESS_ID = 4

    @task
    def seckill_task(self):
        if not SHARED_HEADERS:
            return  # 如果登录失败，就不发请求

        self.client.post(
            f"/api/seckill/{self.EVENT_ID}/buy/",
            json={"address_id": self.ADDRESS_ID},
            headers=SHARED_HEADERS
        )