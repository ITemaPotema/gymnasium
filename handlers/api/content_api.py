from redis import asyncio as aioredis
from decouple import config
from .base_api import BaseApi


class ContentApi(BaseApi):
    def __init__(self, tg_id):
        super().__init__(tg_id)

    async def buy_extra_post(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)
        extra_post_cost = int(config("EXTRA_POST_COST"))

        user_amount = int(await redis.get(f"user:{self.tg_id}:profit"))

        extra_posts_count = await redis.get(f"user:{self.tg_id}:extra")

        if extra_posts_count:
            extra_post_cost = extra_post_cost * (int(extra_posts_count) + 1)
            # вычисляем стоимость покупки доп поста в зависимости от того сколько их у пользователя

        if user_amount < extra_post_cost:
            return user_amount - extra_post_cost  # сколько не хватает для покупки

        async with redis.pipeline() as pipe:
            pipe.multi()
            if extra_posts_count:
                pipe.incrby(f"user:{self.tg_id}:extra", 1)

            else:
                pipe.set(f"user:{self.tg_id}:extra", "1")

            pipe.decrby(f"user:{self.tg_id}:profit", extra_post_cost)
            pipe.incrby("bank:balance", extra_post_cost)
            await pipe.execute()
            print("Покупка доп поста")

            return extra_post_cost

    @classmethod
    async def allow_content(cls, user_id,  content, redis=None):
        if redis is None:
            redis = await aioredis.from_url(cls.redis_url, password=cls.redis_password, max_connections=10)

        user_content_list = await redis.lrange(f"user:{user_id}:content_list", 0, -1)

        # проверка, что у пользователя подключена данная опция
        for content_allow in user_content_list:
            if content == content_allow.decode():
                await redis.aclose()
                return True

        return False

    async def buy_content(self, content):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        already_have = await ContentApi.allow_content(self.tg_id, content, redis=redis)

        # если у пользователя уже есть данная опция
        if already_have:
            await redis.aclose()
            return False

        content_cost = int(config("CONTENT_COST"))
        amount = int(await redis.get(f"user:{self.tg_id}:profit"))

        if amount < content_cost:
            await redis.aclose()
            return amount - content_cost  # отрицательный баланс будет сигнализировать о том, что недостаточно средств

        # транзакция по покупке опции
        async with redis.pipeline() as pipe:
            pipe.multi()
            pipe.rpush(f"user:{self.tg_id}:content_list", content)
            pipe.incrby(f"bank:balance", content_cost)
            pipe.decrby(f"user:{self.tg_id}:profit", content_cost)
            await pipe.execute()
            return content_cost

