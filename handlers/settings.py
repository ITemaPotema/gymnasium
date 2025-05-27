from handlers.api.auth_api import AuthApi, ProfileStatus
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message, TelegramObject
from aiogram import BaseMiddleware, Bot
from redis import asyncio as aioredis
from decouple import config
import time
from typing import Any, Callable, Dict, Awaitable
import aiohttp
import ujson

all_forms = [
    "6А", "6Б", "6В", "6Г",
    "7А", "7Б", "7В", "7Г", "7Д",
    "8А", "8Б", "8В", "8Д",
    "9А", "9Б", "9В", "9Г",
    "10А", "10Б", "10В", "10Г",
    "11А", "11Б"
]


class CheckAuthFilter(Filter):
    async def  __call__(self, request: CallbackQuery | Message):
        user_id = request.from_user.id

        auth_api = AuthApi(user_id)
        result = await auth_api.login()

        if result.status == ProfileStatus.HAS_PROFILE:
            token = result.token
            is_admin = result.is_admin

            return {"token": token, "is_admin": is_admin}

        else:
            if type(request) == CallbackQuery:
                await request.message.answer("Создайте профиль, чтобы воспользоваться этой функцией!(/personal)")
            else:
                await request.answer("Создайте профиль, чтобы воспользоваться этой функцией!(/personal)")

            return False


redis_domain = "localhost" # config("REDIS_DOMAIN")
redis_password = None # config("REDIS_PASSWORD")

async def is_user_banned(user_id: int):
    redis = await aioredis.from_url(f"redis://{redis_domain}:6379/0", password=redis_password, max_connections=10,
                                    decode_responses=True)

    for user in await redis.smembers("ban_list"):
        tg_id, expiry = user.split(":")

        if str(user_id) == tg_id:
            if int(expiry) == -1: # пользователь забанен навсегда
                return True

            if int(time.time() > int(expiry)):
                await redis.srem("ban_list", user) # удаляем пользователя если срок бана истёк
                return False

            else:
                return True

    return False



class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self,
                       handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]
    ) -> Any:
        user = data["event_from_user"]
        user_id = user.id

        if await is_user_banned(user_id):
            await event.answer(
                "🚫 Вы были заблокированы, и срок бана ещё не истёк!"
            )
            return

        else:
            return await handler(event, data)
