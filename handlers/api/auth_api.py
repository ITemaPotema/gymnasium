import aiohttp
from redis import asyncio as aioredis
import ujson
from dataclasses import dataclass
from decouple import config
import enum
from .base_api import BaseApi


class CreateStatus(enum.Enum):
    SUCCESS = "success"
    NOT_AUTHENTICATED = "not_authenticated"

@dataclass
class CreateAnswer:
    status: CreateStatus


class ProfileStatus(enum.Enum):
    NO_PROFILE = "no_profile"
    HAS_PROFILE = "has_profile"

admin_id = config("ADMIN_ID")

@dataclass
class TokenResult:
    token: str
    status: ProfileStatus
    is_admin: bool = False

class AuthApi(BaseApi):
    def __init__(self, tg_id):
        super().__init__(tg_id)

    async def login(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password, max_connections=10, decode_responses=True)
        value = await redis.get(f"user:{self.tg_id}:token")

        if value: # если в redis есть сохранённый токен
            token = value
            is_admin = await redis.sismember("admins", str(self.tg_id))
            await redis.aclose()
            return TokenResult(token=token, status=ProfileStatus.HAS_PROFILE, is_admin=bool(is_admin))

        signature = BaseApi.generate_signature(self.tg_id, self.secret_key) # подписываем запрос общим секретным ключом

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            data = {
                "user_id": self.tg_id,
            }
            headers = {
                "X-Signature": signature
            }
            async with session.post(f"{self.app_url}/sign_in", json=data, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    is_admin = data["is_admin"]
                    token = data["access_token"]

                    # синхронизируем redis со значением из бд
                    if is_admin:
                        if not await redis.sismember("admins", str(self.tg_id)):
                            await redis.sadd("admins", str(self.tg_id))

                    else:
                        if await redis.sismember("admins", str(self.tg_id)):
                            await redis.srem("admins", str(self.tg_id))

                    await redis.set(f"user:{self.tg_id}:token", token) # получаем и сохраняем access token в redis
                    await redis.expire(f"user:{self.tg_id}:token", 60 * 15) # на 15 мин
                    await redis.aclose()
                    return TokenResult(token=token, status=ProfileStatus.HAS_PROFILE, is_admin=is_admin)

                elif resp.status == 404:
                    await redis.aclose()
                    return TokenResult(token="", status=ProfileStatus.NO_PROFILE)

                else:
                    return False


    async def auth_iphone(self, tg_name, vk_id):
        data = {
            "tg_name": tg_name,
            "tg_id": self.tg_id,
            "vk_id": vk_id
        }

        signature = BaseApi.generate_signature(str(self.tg_id), self.secret_key)
        headers = {"X-Signature": signature}

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            async with session.post(f"{self.app_url}/auth_iphone", json=data, headers=headers) as resp:
                status = resp.status
                return status


    async def create_profile(self, user_data):
        signature = BaseApi.generate_signature(self.tg_id, self.secret_key)

        headers = {"X-Signature": signature}

        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            async with session.post(f"{self.app_url}/profile/create", json=user_data, headers=headers) as resp:
                if resp.status == 200:
                    redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                                        max_connections=10, decode_responses=True)
                    if not (str(self.tg_id) == admin_id): # проверка на суперадмина
                        await redis.set(f"user:{self.tg_id}:profit", "0")

                    else:
                        async with redis.pipeline() as pipe: # создание профиля суперадмина
                            pipe.multi()
                            pipe.set(f"user:{self.tg_id}:extra", "10")
                            pipe.rpush(f"user:{self.tg_id}:content_list", "stat")
                            pipe.set(f"user:{self.tg_id}:profit", "750")
                            pipe.sadd(f"admins", str(self.tg_id))
                            await pipe.execute()

                    await redis.aclose()
                    return CreateAnswer(status=CreateStatus.SUCCESS)

                if resp.status == 401:
                    return CreateAnswer(status=CreateStatus.NOT_AUTHENTICATED)


