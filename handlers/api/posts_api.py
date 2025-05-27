import aiohttp
from redis import asyncio as aioredis
import ujson
from dataclasses import dataclass
import json
from decouple import config
from .base_api import BaseApi


@dataclass
class PaymentResult:
    success: bool
    amount: int

class PostsApi(BaseApi):
    def __init__(self, tg_id, token=None):
        super().__init__(tg_id)
        self.token = token

    async def create_post_db(self, text, content, describe, type):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"text": text, "content": content, "describe": describe, "type": type}

            async with session.post(f"{self.app_url}/post/create", headers=headers, json=data) as resp:
                if resp.status == 200:
                    await redis.incrby(f"user:{self.tg_id}:posts_today", 1) # увеличиваем счётчик созданных постов на сегодня
                    await redis.aclose()
                    print("Создание поста")
                    return True

                return False


    async def pay_for_post(self, advance=None):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                            max_connections=10)

        if advance is True: # покупается пост особенной категории
            cost = int(config("ADVANCE_CREATE"))
            profit = await redis.get(f"user:{self.tg_id}:profit")
            profit = int(profit.decode())

            if cost > profit:
                return PaymentResult(success=False, amount=cost - profit)

            async with redis.pipeline() as pipe:
                pipe.multi()
                pipe.incrby("bank:balance", cost) # увеличиваем баланс банка
                pipe.decrby(f"user:{self.tg_id}:profit", cost) # уменьшаем баланс пользователя
                await pipe.execute()

            return PaymentResult(success=True, amount=cost)

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with session.post(f"{self.app_url}/post/pay", headers=headers) as resp:
                data = await resp.json()
                if resp.status == 200:
                    amount = data["paid"]

                    await redis.incrby("bank:balance", amount)
                    await redis.aclose()

                    return PaymentResult(success=True, amount=amount)

                if resp.status == 400:
                    return PaymentResult(success=False, amount=data["amount"])

    async def load_post_stat(self):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:

            headers = {"Authorization": f"Bearer {self.token}"}
            async with session.get(f"{self.app_url}/post/stat", headers=headers) as resp: # подгружаем посты юзера из бд
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                                    max_connections=10)
                    data = await resp.json()
                    data_json_string = json.dumps(data)

                    await redis.set(f"user:{self.tg_id}:posts:stat", data_json_string) # сохраняем в redis

                    return data

                return False

    async def get_post_stat(self, offset):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                        max_connections=10)

        data = await redis.get(f"user:{self.tg_id}:posts:stat")
        data = json.loads(data)

        return data["posts"][offset]


    async def allow_post(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        extra_post_count = await redis.get(f"user:{self.tg_id}:extra")
        allow_count = int(config("POSTS_PER_DAY"))

        if extra_post_count:
            allow_count += int(extra_post_count)

        count = await redis.get(f"user:{self.tg_id}:posts_today") # сколько уже постов пользователь создал сегодня

        if not count:
            await redis.setex(f"user:{self.tg_id}:posts_today", 24 * 60 * 60, "0")  # инициализируем счётчик постов на 24 часа
            await redis.aclose()
            return True

        if int(count) < allow_count:
            return True

        return False


    async def get_pupil_liked_post(self, post_id):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        post_actions = await redis.lrange(f"{post_id}:post:actions", 0, -1)

        likers = []

        for action_data in post_actions:
            user_id, action = action_data.decode().split(":")

            if action == "like":
                likers.append(int(user_id)) # список тех, кто лайкнул данный пост

        # запрос в бд, чтобы узнать информацию о лайкнувших
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"likers": likers}

            async with session.post(f"{self.app_url}/post/likers/data", headers=headers, json=data) as resp:
                if resp.status == 200:
                    pupils = await resp.json()
                    return pupils["data"]

                return False

    # пост можно лайкнуть только один раз, соответсвующая проверка
    @staticmethod
    async def check_action_allow(redis, post_id, tg_id):
        tg_id = str(tg_id)
        post_actions = await redis.lrange(f"{post_id}:post:actions", 0, -1)

        for user in post_actions:
            if user.decode().startswith(tg_id):
                return False

        return True

    # реакция на пост
    async def post_action(self, post_id: int, creator_id, action):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        if not await self.check_action_allow(redis, post_id, self.tg_id):
            return False

        if action == "like":
            to_author = int(config("LIKE_COST")) # сколько нужно выплатить автору

        else:
            to_author = 0

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with session.post(f"{self.app_url}/post/reaction/{action}/{post_id}", headers=headers) as resp:
                if resp.status == 200:
                    exist = await redis.exists(f"{post_id}:post:actions")
                    await redis.rpush(f"{post_id}:post:actions", f"{str(self.tg_id)}:{action}") # добавляем юзера в список просмотревших данный пост

                    if not exist:
                        await redis.expire(f"{post_id}:post:actions", 24 * 60 * 60)
                        # так как пост будет удалён из бд через 24 часа, то нужно удалить и этот ключ

                    # транзакция по выплате средств создателю поста за лайк
                    async with redis.pipeline() as pipe:
                        pipe.multi()
                        pipe.incrby(f"user:{creator_id}:profit", to_author)
                        pipe.decrby("bank:balance", to_author)
                        await pipe.execute()

                    await redis.aclose()

                    return True

                return False

    @staticmethod
    async def load_new_posts(redis, token, tg_id, app_url, only_negative):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {token}"}
            params = {"only_negative": only_negative}

            async with session.get(f"{app_url}/post/feed", params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json() # получаем данные из бд

                    for post in data:
                        post = json.dumps(post)
                        await redis.rpush(f"user:{tg_id}:posts", post) # сохраняем в redis очередь

                    return True

                return False

    async def delete_posts_in_cache(self): # очищает redis очередь юзера от старых постов
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        await redis.delete(f"user:{self.tg_id}:posts")
        await redis.aclose()

    async def watch_post(self, only_negative=0):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        post_data = await redis.lpop(f"user:{self.tg_id}:posts")

        if not post_data:
            # подгружаем новые посты, если они закончились в локальной очереди redis
            load_posts = await self.load_new_posts(redis, self.token, self.tg_id, self.app_url, only_negative)

            if not load_posts:
                return False

            post_data = await redis.lpop(f"user:{self.tg_id}:posts") # извлекаем пост из очереди

        post = json.loads(post_data)
        return post

    # удаление поста
    async def delete_post(self, post_id: int):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {"post_id": post_id}

            async with session.delete(f"{self.app_url}/post/delete", headers=headers, params=params) as resp:
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                                    max_connections=10)

                    # удаляем ключ с реакциями под постом
                    await redis.delete(f"{post_id}:post:actions")
                    await redis.aclose()

                    print("Пост удалён")
                    return True
