from aiogram import Bot
import aiohttp
from redis import asyncio as aioredis
import ujson
import json
from .base_api import BaseApi


class UserProfileApi(BaseApi):
    def __init__(self, tg_id, token):
        super().__init__(tg_id)
        self.token = token


    async def get_profile(self):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with session.get(f"{self.app_url}/profile", headers=headers) as resp:
                if resp.status == 200:
                    profile = await resp.json()
                    return profile

                else:
                    return False

    async def edit_profile(self, data, category): # category = photo | info
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}
            request_data = {"data": data}

            async with session.patch(f"{self.app_url}/profile/edit/{category}", headers=headers, json=request_data) as resp:
                if resp.status == 200:
                    return True

                return False


    async def deactivate_profile(self):
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            headers = {"Authorization": f"Bearer {self.token}"}

            async with session.delete(f"{self.app_url}/profile/deactivate", headers=headers) as resp:
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)
                    async for key in redis.scan_iter(match=f"user:{self.tg_id}:*"): # удаляем все связанные с пользователем ключи
                        await redis.delete(key)
                    return True

                else:
                   return False


class ProfileProgress(BaseApi):
    def __init__(self, tg_id):
        super().__init__(tg_id)


    async def get_profile_progress(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        data = await redis.getdel(f"user:{self.tg_id}:profile_progress")

        if data:
            return json.loads(data)

        return False


    async def save_profile_progress(self, data):
        data = json.dumps(data)

        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10)

        await redis.setex(f"user:{self.tg_id}:profile_progress", 60 * 10, data)
        await redis.aclose()




