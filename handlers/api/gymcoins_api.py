import aiohttp
from redis import asyncio as aioredis
import ujson
from .base_api import BaseApi
import time

class GymcoinsApi(BaseApi):
    def __init__(self, tg_id, token=None):
        super().__init__(tg_id)
        self.token = token

    async def get_balance(self):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.get(f"{self.app_url}/user/balance", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["balance"]

                return False

    async def get_profit(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        profit = await redis.get(f"user:{self.tg_id}:profit")
        profit = int(profit)

        return profit

    async def withdraw_funds(self, amount, source):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)
        profit = int(await redis.get(f"user:{self.tg_id}:profit"))

        if amount > profit:
            return False

        time_stamp = str(int(time.time()))  # временная метка
        query_generate = time_stamp + str(self.tg_id)  # данные для подписи, обеспечивают уникальность query_id
        query_id = BaseApi.generate_signature(query_generate, self.secret_key)[:16]  # генерируем сигнатуру используя общий секретный ключ, query_id - первые 16 символов

        query = f"withdraw:{query_id}:{time_stamp}"

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {"funds_amount": amount, "query": query}

            async with session.post(f"{self.app_url}/gymcoins/withdraw", headers=headers, params=params) as resp:
                if resp.status == 200:
                    if source == "profit":
                        await redis.decrby(f"user:{self.tg_id}:profit", amount)

                    else:
                        await redis.decrby("bank:balance", amount)

                    await redis.aclose()

                    return True

                return False