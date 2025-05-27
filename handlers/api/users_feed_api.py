import aiohttp
from redis import asyncio as aioredis
import ujson
import json
from .base_api import BaseApi


class UserFeedApi(BaseApi):
    def __init__(self, tg_id, token=None):
        super().__init__(tg_id)
        self.token = token

    @staticmethod
    async def get_users_from_db(token, app_url, form):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {token}"}
            async with session.get(f"{app_url}/users/form/{form}", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data

    async def get_users_from_form(self, form):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)
        data = await redis.get(f"users:{form}")

        if data:
            return json.loads(data)

        data_all_users = await UserFeedApi.get_users_from_db(self.token, self.app_url, form) # подгружаем учеников конкретного класса из бд

        await redis.set(f"users:{form}", json.dumps(data_all_users)) # кэшируем в redis на 1 мин
        await redis.expire(f"users:{form}", 60)

        await redis.aclose()
        return data_all_users

    @staticmethod
    async def get_users_data_feed(token, app_url, sex, form_min=6):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {token}"}

            if not sex:
                params = (("form_min", form_min), ("sex", 1), ("sex", 2))
            else:
                params = (("form_min", form_min), ("sex", sex))

            async with session.get(f"{app_url}/users/feed", params=params, headers=headers) as resp:
                if resp.status == 200:
                    users: list = await resp.json()
                    return users

                return False

    async def get_user_from_feed(self, sex, form_min, start=False):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        if start:
            await redis.delete(f"user:{self.tg_id}:feed:users") # при старте ленты нужно очистить очередь

        user = await redis.rpop(f"user:{self.tg_id}:feed:users")

        if not user:
            # получаем учеников из бд по определённым фильтрам(limit = 10 записей)
            users = await UserFeedApi.get_users_data_feed(self.token, self.app_url, sex, form_min)

            if not users:
                return False

            for user in users:
                await redis.rpush(f"user:{self.tg_id}:feed:users", json.dumps(user)) # кэшируем в redis

            user = await redis.rpop(f"user:{self.tg_id}:feed:users")

        return json.loads(user)


    @staticmethod
    async def like_db(app_url, tg_id, token):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {token}"}
            params = {"tg_id": tg_id}
            async with session.post(f"{app_url}/like", params=params, headers=headers) as resp:
                if resp.status == 200:
                    return True

                else:
                    return False

    async def like_user(self, who_id):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        pupils = await redis.lrange(f"user:{self.tg_id}:donations", 0, -1)

        # проверка, что юзер не в списке недавно лайкнувших профиль self.tg_id
        if pupils:
            for pupil_tg_id in pupils:
                if str(who_id) == pupil_tg_id.decode():
                    await redis.aclose()
                    return False

        answer = await UserFeedApi.like_db(self.app_url, who_id, self.token) # лайк в бд

        if answer:
            await redis.rpush(f"user:{self.tg_id}:donations", str(who_id)) # добавление в список тех, кого лайкнул tg_id
            if not pupils:
                await redis.expire(f"user:{self.tg_id}:donations", 24 * 60 * 60) # через 24 часа можно будет опять лайкнуть пользователя

            await redis.aclose()
            return True

        return False

    async def check_request_history(self, receiver_id: int):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)
        length = await redis.llen(f"user:{self.tg_id}:recently")
        receivers = await redis.lrange(f"user:{self.tg_id}:recently", 0, -length) # получаем список тех, кому пользователь недавно отправлял заявку
        await redis.aclose()

        receiver_in_list = False

        if receivers: # проверка, что receiver_id нет в этом списке
            for receiver in receivers:
                receiver = int(receiver.decode())
                if receiver == receiver_id:
                    receiver_in_list = True
                    break

        return receiver_in_list


    async def send_exchange_request(self, receiver_id, sender_username, message):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        # данные заявки
        data = {
            "message": message,
            "sender_id": self.tg_id,
            "sender_username": sender_username
        }

        data_json = json.dumps(data)

        await redis.lpush(f"user:{receiver_id}:requests", data_json) # сохраняем заявку в список получателя
        exist = await redis.exists(f"user:{self.tg_id}:recently")

        await redis.rpush(f"user:{self.tg_id}:recently", str(receiver_id)) # добавляем  получателя в список недавно отправленных заявок

        if not exist:
            await redis.expire(f"user:{self.tg_id}:recently", 24 * 60 * 60)
        await redis.aclose()


    async def get_requests(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        data_json = await redis.lpop(f"user:{self.tg_id}:requests") # извлекаем заявку из redis

        if not data_json:
            return False

        data = json.loads(data_json)
        await redis.aclose()

        return data

    async def get_amount_requests(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        length = await redis.llen(f"user:{self.tg_id}:requests") # узнаём количество заявок
        await redis.aclose()

        return length