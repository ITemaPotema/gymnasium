import asyncio
import aiocron
from handlers.bot_config import bot, dp
from handlers.base import base_router
from handlers.registration import registration_router
from handlers.user_search import search_router
from handlers.posts import posts_router
from handlers.gymcoins import gymcoins_router
from handlers.subscriptions import options_router
from handlers.admin import admin_router
from handlers.anonymous_chat import chat_router
from redis import asyncio as aioredis
from handlers.api.admin_api import AdminApi
from handlers.api.auth_api import AuthApi
from decouple import config
from handlers.settings import BanCheckMiddleware
from aiocron import crontab

async def main():
    dp.include_router(base_router)
    dp.include_router(registration_router)
    dp.include_router(search_router)
    dp.include_router(posts_router)
    dp.include_router(gymcoins_router)
    dp.include_router(options_router)
    dp.include_router(admin_router)
    dp.include_router(chat_router)
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())

    redis_domain = "localhost" # config("REDIS_DOMAIN")
    password = None # config("REDIS_PASSWORD")

    redis = await aioredis.from_url(f"redis://{redis_domain}:6379/0", password=password, max_connections=10)

    # инициализация нужных ключей и привилегий админов
    async with redis.pipeline() as pipe:
        pipe.multi()
        pipe.set("bank:balance", "1000000000") # баланс банка
        pipe.set("chat_online", "0")
        await pipe.execute()

    @crontab("0 0 * * *", start=True) # каждый день в полночь
    async def daily_post_payments():
        admin_id = int(config("ADMIN_ID"))
        auth_api = AuthApi(admin_id)
        res = await auth_api.login()
        admin_api = AdminApi(admin_id, res.token)  # выполняем задачу от имени админа

        await admin_api.pay_to_win_posts(bot)

    print("Бот запущен")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())