
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from .api.content_api import ContentApi
from .interface import get_options_keyboard
from decouple import config
from .settings import CheckAuthFilter


options_router = Router()


@options_router.callback_query(lambda cal: cal.data == "commands:options", CheckAuthFilter())
async def show_list_of_options(callback: CallbackQuery):
    keyboard = get_options_keyboard()
    await callback.message.answer("Здесь ты можешь купить дополнительные опции за монеты автора:", reply_markup=keyboard)


@options_router.callback_query(lambda cal: cal.data.startswith("option"))
async def choose_option(callback: CallbackQuery):
    option = callback.data.split(":")[1]
    option_cost = config("CONTENT_COST")
    extra_post_cost = config("EXTRA_POST_COST")

    answers = {
        "extra_post": "Эта опция позволяет создавать на один пост в день больше. В отличие от других может быть куплена неоднократно, но каждый раз стоимость будет выше.",
        "stat": "Эта опция позволяет видеть тех, кто поставил лайк Вашим постам. Бот пришлёт Вам файл.\n"
                "Внимание❗ Файл может некорректно отображаться через проводник telegram, поэтому его следует скачать на устройство и открыть через 'Загрузки'"
    }

    button = [[InlineKeyboardButton(text="Купить", callback_data=f"buy:{option}")]]
    kb = InlineKeyboardMarkup(inline_keyboard=button)

    cost_text = f"Стоимость = {extra_post_cost}💡 * n, n = кол во доп постов, которое Вы уже купили" if option == "extra_post" else f"Стоимость = {option_cost}💡"
    text = answers[option] + "\n\n" + cost_text

    await callback.message.answer(text=text, reply_markup=kb)


@options_router.callback_query(lambda cal: cal.data.startswith("buy"))
async def buy_option(callback: CallbackQuery):
    user_id = callback.from_user.id
    option = callback.data.split(":")[1]
    content_api = ContentApi(user_id)

    if option == "extra_post":
        result = await content_api.buy_extra_post()

    else:
        result = await content_api.buy_content(option)

    if result > 0:
        await callback.message.answer(text=f"Успешно! Списано {result}💡")

    elif result is False:
        await callback.message.answer(text="Эта опция уже подключена!")

    else:
        await callback.message.answer(text=f"Не хватает {-result}💡")



