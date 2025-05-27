from aiogram import Bot
import aiohttp
from redis import asyncio as aioredis
from dataclasses import dataclass
from .base_api import BaseApi
import enum

class SearchStatus(enum.Enum):
    ALREADY_EXIST = "already_exist"
    WAITING = "waiting"
    SUCCESS = "success"

@dataclass
class SearchChatResult:
    status: SearchStatus
    partner_id: int = None

class ChatApi(BaseApi):
    def __init__(self, tg_id):
        super().__init__(tg_id)

    async def search_user_to_chat(self) -> SearchChatResult:
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                      decode_responses=True)

        # Проверяем, есть ли уже активный чат
        if await redis.hexists("active_chats", str(self.tg_id)):
            await redis.aclose()
            return SearchChatResult(status=SearchStatus.ALREADY_EXIST)

        # Достаём партнёра из очереди
        partner_id = await redis.lpop("search_queue")

        if partner_id:
            partner_id = int(partner_id)

            async with redis.pipeline() as pipe:
                pipe.multi()
                pipe.hset("active_chats", str(self.tg_id), partner_id)
                pipe.hset("active_chats", str(partner_id), self.tg_id)
                pipe.incrby("chat_online", 2)
                await pipe.execute()

            await redis.aclose()
            return SearchChatResult(status=SearchStatus.SUCCESS, partner_id=partner_id)

        else:
            # Если партнёра нет, добавляем себя в очередь
            await redis.rpush("search_queue", self.tg_id)
            await redis.aclose()
            return SearchChatResult(status=SearchStatus.WAITING)

    async def get_online(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                      decode_responses=True)
        return await redis.get("chat_online")

    async def stop_chat(self, partner_id: int) -> bool:
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                      decode_responses=True)
        if not await redis.hexists("active_chats", str(self.tg_id)): # если чат уже удалён
            return True

        try:
            async with redis.pipeline() as pipe:
                pipe.multi()
                pipe.hdel("active_chats", str(self.tg_id))
                pipe.hdel("active_chats", str(partner_id))
                pipe.decrby("chat_online", 2)
                await pipe.execute()

            return True

        except Exception as e:
            print(f"Ошибка при удалении чата: {e}")
            return False
        finally:
            await redis.aclose()

    async def cancel_waiting(self) -> bool:
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                      decode_responses=True)
        try:
            await redis.lrem("search_queue", 0, str(self.tg_id))
            return True
        except Exception as e:
            print(f"Ошибка при отмене поиска: {e}")
            return False
        finally:
            await redis.aclose()

    async def get_partner_id(self):
        redis = await aioredis.from_url(self.redis_url, password=self.redis_password,
                                      decode_responses=True)
        try:
            partner_id = await redis.hget("active_chats", str(self.tg_id))
            return int(partner_id) if partner_id else None
        except Exception as e:
            print(f"Ошибка при получении partner_id: {e}")
            return None
        finally:
            await redis.aclose()
