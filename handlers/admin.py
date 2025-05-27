from aiogram import Router
from aiogram.types import CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .api.admin_api import AdminApi
from .bot_config import bot
from .settings import CheckAuthFilter, is_user_banned
from .interface import user_card_action_kb

admin_router = Router()


@admin_router.callback_query(lambda cal: cal.data.startswith("admin:delete_post"), CheckAuthFilter())
async def delete_bad_post(callback: CallbackQuery, token: str):
    admin_id = callback.from_user.id
    post_id, creator_id = callback.data.split(":")[2:4]
    admin_api = AdminApi(admin_id, token)

    delete_result = await admin_api.delete_post(post_id)

    if delete_result:
        await callback.message.delete()
        await callback.message.answer("Пост удалён✅")
        warning_text = ("Предупреждение❗❗❗ \n\n"
                        "Контент одного из Ваших постов оказался неприемлимым и соответсвенно был удалён модерацией.\n\n"
                        "Уважайте других и не публикуйте всякую ерунду❗")

        await bot.send_message(creator_id, text=warning_text)


@admin_router.callback_query(lambda cal: cal.data.startswith("promotion"), CheckAuthFilter())
async def promote_user_up_down(callback: CallbackQuery, token: str, is_admin: bool):
    to_promote_id, action = callback.data.split(":")[1:]
    admin_id = callback.from_user.id
    admin_api = AdminApi(tg_id=admin_id, token=token)

    if action == "upgrade":
        result = await admin_api.promote_user(int(to_promote_id))
        text = "Пользователь добавлен в число админов✅"
        new_kb = user_card_action_kb(int(to_promote_id), is_admin, True)

    else:
        result = await admin_api.downgrade_user(int(to_promote_id))
        text = "Пользователь исключён из числа админов❌"
        new_kb = user_card_action_kb(int(to_promote_id), is_admin, False)

    if result:
        await callback.message.answer(text=text)
        await callback.message.edit_reply_markup(reply_markup=new_kb)



class BanStates(StatesGroup):
    duration = State()
    message = State()


@admin_router.callback_query(lambda cal: cal.data.startswith("admin:ban_user"), CheckAuthFilter())
async def start_baning_process(callback: CallbackQuery, state: FSMContext):
    delete_id = int(callback.data.split(":")[2])

    if await is_user_banned(delete_id):
        await callback.message.answer(text="Пользователь уже заблокирован!")
        return

    await state.update_data(delete_id=delete_id)

    await callback.message.answer("Введи сообщение пользователю:")
    await state.set_state(BanStates.message)


@admin_router.message(StateFilter(BanStates.message))
async def get_ban_message(message: Message, state: FSMContext):
    if not message.text:
        await message.answer(text="Введи текст!")
        return

    ban_message = message.text
    await state.update_data(message=ban_message)

    btn = [[KeyboardButton(text="Навсегда😈")]]
    keyboard = ReplyKeyboardMarkup(keyboard=btn, resize_keyboard=True)

    await message.answer(text="Введи длительность бана(в часах):", reply_markup=keyboard)
    await state.set_state(BanStates.duration)


@admin_router.message(StateFilter(BanStates.duration), CheckAuthFilter())
async def ban_user(message: Message, state: FSMContext, token: str):
    if not message.text.isdigit() and message.text != "Навсегда😈":
        await message.answer("Ошибка! Неверный формат!")
        return

    delete_id = await state.get_value("delete_id")
    ban_message = await state.get_value("message")

    duration = int(message.text) if message.text.isdigit() else -1 # -1 -> пользователь заблокирован навсегда

    admin_id = message.from_user.id
    admin_api = AdminApi(tg_id=admin_id, token=token)

    result = await admin_api.ban_user(delete_id, duration)

    if result:
        ban_duration = f"{duration} час(а/ов)" if duration != -1 else "навсегда"
        text = (f"Внимание❗ Вы были заблокированы модерацией и теперь {ban_duration} не сможете пользоваться ботом\n\n"
                f"Cообщение от модерации:\n"
                f"{ban_message}")

        await bot.send_message(delete_id, text=text)
        await message.answer("Пользователь забанен🚫", reply_markup=ReplyKeyboardRemove())

    await state.clear()