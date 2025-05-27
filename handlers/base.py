from aiogram import Router
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from .interface import get_support_keyboard, get_stars_keyboard, get_post_commands, get_search_commands, get_profile_commands
from decouple import config
import asyncio

base_router = Router()


@base_router.message(Command("start"))
async def greeting_with_user(message: Message):
    text =("Добро пожаловать в 'Gymnasium'!\n\n"
            "Это платформа для школьных новостей и знакомств.\n"
            "Скорее осваивайся и стань настоящей легендой школы!\n\n"
            "/help - поможет в освоении"
           )

    await message.answer(text=text)

    special_user_id = int(config("SPECIAL_ID"))

    if message.from_user.id == special_user_id:
        await message.answer_sticker(sticker="CAACAgIAAxkBAAEOKcNn9BmjYCp6hmZJyG0xmnDQjoLaUgAC7RkAAk6H-Ei_b1reCn5mazYE")
        await asyncio.sleep(2)
        await message.answer_sticker(sticker="CAACAgIAAxkBAAEO2QhoF1jhqkGCR9iy1hkG46qyArOuwAACFQMAAuSkCAe7gnojkiZa8zYE")
        await asyncio.sleep(2)
        await message.answer_sticker(sticker="CAACAgIAAxkBAAEO2RZoF1nI31soK1SwQppJxaU9P0yFiwACHAADw1YDHgaZGGIHt0S3NgQ")



@base_router.message(Command("cancel"))
async def cancel_state(message: Message, state: FSMContext):
    await message.answer("Все состояния сброшены.")
    await state.clear()


@base_router.message(Command("support"))
async def ask_support(message: Message):
    keyboard = get_support_keyboard()

    text = ("Дорогой пользователь!\n\n Спасибо, за интерес, проявленный к данному проекту.\n"
            "Будем рады любой финансовой от Вас помощи. Если Вам действительно нравится этот проект, и Вы хотите облегчить его финансовое содержание, можете помочь двумя способами:"
           )

    await message.answer(text=text, reply_markup=keyboard)


@base_router.callback_query(lambda cal: cal.data.startswith("support"))
async def send_support_agree(callback: CallbackQuery):
    type_support = callback.data.split(":")[1]

    if type_support == "stars":
        prices = [LabeledPrice(label="XTR", amount=100)]
        await callback.message.answer_invoice(
            title="Поддержать проект",
            description="Поддержать проект на 100 звёзд!",
            prices=prices,
            provider_token="",
            payload="channel_support",
            currency="XTR",
            reply_markup=get_stars_keyboard(),
        )

    else:
        credit_card = config("CREDIT_CARD")
        await callback.message.answer(f"Т-Банк: {credit_card}")


@base_router.pre_checkout_query()
async def pre_check(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)


@base_router.message(lambda mes: mes.successful_payment is True)
async def say_thanks(message: Message):
    await message.answer(text="Спасибо за вашу поддержку!🤗🙏❤")


@base_router.message(Command("personal"))
async def profile_abilities(message: Message):
    keyboard = get_profile_commands()

    await message.answer(text="Личное:", reply_markup=keyboard)


@base_router.message(Command("pupils"))
async def pupils_abilities(message: Message):
    keyboard = get_search_commands()

    await message.answer(text="Знакомства и поиск учеников:", reply_markup=keyboard)


@base_router.message(Command("posts"))
async def pupils_abilities(message: Message):
    keyboard = get_post_commands()

    await message.answer(text="Операции с постами:", reply_markup=keyboard)



@base_router.message(Command("help"))
async def help_information(message: Message):
    text = ("Ещё раз привет! Это памятка расскажет тебе об основных функциях платформы:\n\n"
            "1. Пройди авторизацию(/authorization) и создай личный профиль(/personal).\n\n"
            "2. /pupils - поиск ученика по классам, а также лента из учеников школы. \n\n"
            "3. /posts - создание постов, об этом подробнее:\n"
            "Всё завязано на школьной виртуальной валюте Gymcoins💎, суть вот в чём:\n"
            "Вы тапаете 💎 -> тратите на создание постов.\n"
            "За лайки автор поcта получает специальную валюту 💡, баланс которой пользователь может посмотреть в 'Кошельке автора'.\n"
            "Её он может либо конвертировать в 💎, либо потратить на создания спец постов(гс/кружочки/видео) или на покупку опций.\n")

    await message.answer(text=text)


@base_router.message(Command("about"))
async def about_me(message: Message):
    channel_url = config("MY_CHANNEL")
    text = (f"Если Вам интересен данный проект, подписывайтесь на канал: {channel_url}\n"
            f"В нём ты найдёшь информацию о будущих обновлениях, а также интересные факты о его создании.\n"
            f"Ты можешь предложить свои идеи и мы обязательно их рассмотрим.\n"
            f"Сделаем вместе ЛУЧШУЮ школьную платформу!")

    await message.answer(text=text)





