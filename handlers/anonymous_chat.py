from aiogram import Router
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command, Filter
from .bot_config import bot
from .interface import get_cancel_kb, get_chat_kb
from .api.chat_api import ChatApi, SearchStatus
from .settings import CheckAuthFilter

chat_router = Router()

@chat_router.message(Command("chat"))
async def start_anonymous_chat(message: Message):
    user_id = message.from_user.id
    chat_api = ChatApi(user_id)
    online = await chat_api.get_online()

    kb = get_chat_kb(online=online)
    await message.answer("Добро пожаловать в анонимный чат!", reply_markup=kb)


@chat_router.callback_query(lambda cal: cal.data == "chat:search", CheckAuthFilter())
async def search_dialog_partner(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_api = ChatApi(user_id)
    result = await chat_api.search_user_to_chat()

    if result.status == SearchStatus.SUCCESS:
        partner_id = result.partner_id

        text = "Собеседник найден! Начинайте общение."
        btn = [[KeyboardButton(text="Закончить беседу🛑")]]
        kb = ReplyKeyboardMarkup(keyboard=btn, resize_keyboard=True)

        await callback.message.answer(text=text, reply_markup=kb)
        await bot.send_message(chat_id=partner_id, text=text, reply_markup=kb)

    if result.status == SearchStatus.ALREADY_EXIST:
        await callback.message.answer(text="Вы уже состоите в активном чате!")

    if result.status == SearchStatus.WAITING:
        kb = get_cancel_kb()

        await callback.message.answer(text="Ищу собеседника🔍...", reply_markup=kb)



@chat_router.callback_query(lambda cal: cal.data == "chat:cancel")
async def cancel_chat_waiting(callback: CallbackQuery):
    user_id = callback.from_user.id
    chat_api = ChatApi(user_id)

    await chat_api.cancel_waiting()
    await callback.message.answer(text="Вы вышли из очереди.")


class HasActiveChatFilter(Filter):
    async def __call__(self, message: Message):
        user_id = message.from_user.id
        chat_api = ChatApi(user_id)

        partner_id = await chat_api.get_partner_id()

        if not partner_id:
            return False

        return {"partner_id": partner_id, "chat_api": chat_api}


@chat_router.message(HasActiveChatFilter(), lambda mes: mes.text == "Закончить беседу🛑")
async def finish_dialog(message: Message, partner_id: int, chat_api: ChatApi):
    await chat_api.stop_chat(partner_id)
    online = await chat_api.get_online()
    kb = get_chat_kb(online=online)

    await bot.send_message(chat_id=partner_id, text="Собеседник остановил диалог с Вами!🛑", reply_markup=ReplyKeyboardRemove())
    await bot.send_message(chat_id=partner_id, text="Найти нового собеседника?", reply_markup=kb)
    await message.answer(text="Беседа завершена!", reply_markup=ReplyKeyboardRemove())
    await message.answer(text="Найти нового собеседника?", reply_markup=kb)


@chat_router.message(HasActiveChatFilter())
async def chatting(message: Message, partner_id: int):
    if not message.text:
        await message.answer(text="Можно отправлять только текстовые сообщения!")
        return

    await bot.send_message(chat_id=partner_id, text=message.text)
