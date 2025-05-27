from aiogram import Bot
import aiohttp
from redis import asyncio as aioredis
import ujson
from .base_api import BaseApi
import time

class AdminApi(BaseApi):
    def __init__(self, tg_id, token=None):
        super().__init__(tg_id)
        self.token = token

    async def set_only_negative(self, value: bool):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        await redis.set(f"user:{self.tg_id}:only_negative", int(value))
        await redis.aclose()

    async def only_negative(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        value = await redis.get(f"user:{self.tg_id}:only_negative")
        await redis.aclose()

        return int(value)

    async def delete_post(self, post_id):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            params = {"post_id": post_id}

            async with session.delete(f"{self.app_url}/post/delete", headers=headers, params=params) as resp:
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                                    max_connections=10)
                    await redis.delete(f"{post_id}:post:actions") # вслед за постом удаляем и очередь с реакциями
                    await redis.aclose()

                    print("Пост удалён")
                    return True


    async def pay_to_win_posts(self, bot: Bot):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with session.get(f"{self.app_url}/post/winners", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    amount_sent = data["amount_sent"]
                    users_fractions = data["users_fractions"]

                    async with redis.pipeline() as pipe:
                        pipe.multi()
                        pipe.decrby("bank:balance", amount_sent)
                        for user_id in users_fractions:
                            prize = users_fractions[user_id]["prize"]
                            pipe.incrby(f"user:{user_id}:profit", prize)

                        await pipe.execute()

                    print(f"Ежедневные итоги: {users_fractions}")

                    for user_id in users_fractions:
                        text_begin = (
                            f"Поздравляю! Один или несколько твоих постов попали в ежедневный топ 5 по лайкам!\n\n"
                            f"Твои посты заняли следующие места(место: описание): \n")

                        places = users_fractions[user_id]["places"]
                        text_places = ""

                        for place in places:
                            post_data = places[place]
                            place_text = f"{place} место: {post_data['describe']} - {post_data['likes']}❤\n"
                            text_places += place_text

                        text_end = f"В качестве награды на ваш счёт было зачислено {users_fractions[user_id]['prize']}💡"

                        text = text_begin + text_places + "\n" + text_end

                        await bot.send_message(chat_id=user_id, text=text)

                    await redis.aclose()


    async def promote_user(self, user_id: int):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"tg_id": user_id}

            async with session.patch(f"{self.app_url}/admin/user/promotion/upgrade", headers=headers, json=data) as resp:
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                                    max_connections=10)
                    await redis.sadd("admins", str(self.tg_id))
                    await redis.delete(f"user:{user_id}:token")  # удаляем обычный токен из кэша

                    return True

                else:
                    return False

    async def downgrade_user(self, user_id: int):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            data = {"tg_id": user_id}

            async with session.patch(f"{self.app_url}/admin/user/promotion/downgrade", headers=headers, json=data) as resp:
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                                    max_connections=10)
                    await redis.srem("admins", str(user_id)) # удаляем из списка админов
                    await redis.delete(f"user:{user_id}:token") # удаляем админский токен из кэша
                    return True

                else:
                    return False

    async def ban_user(self, user_id: int, duration_hours: int):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                        max_connections=10)
        if duration_hours == -1: # если блокируем навсегда
            async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
                headers = {"Authorization": f"Bearer {self.token}"}
                data = {"tg_id": user_id}

                # удаляем профиль из бд
                async with session.delete(f"{self.app_url}/admin/user/delete", headers=headers, json=data) as resp:
                    if resp.status == 200:
                        async for key in redis.scan_iter(match=f"user:{user_id}:*"): # удаляем все связанные с пользователем ключи
                            print("key")
                            await redis.delete(key)

                    else:
                        return False

            expire_time = -1  # -1 -> пользователь забанен навсегда

        else:
           expire_time = str(int(time.time()) + duration_hours * 3600)

        await redis.sadd("ban_list", f"{user_id}:{expire_time}") # добавляем пользователя в список забаненных
        await redis.aclose()
        return True
