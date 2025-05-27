from aiogram import Router
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from .api.users_feed_api import UserFeedApi
from .api.auth_api import AuthApi
from .api.profile_api import UserProfileApi
from .interface import (get_pagination_keyboard, get_sex_keyboard, get_form_keyboard,
                        get_feed_keyboard, get_request_keyboard, user_card_action_kb)

from .settings import all_forms, CheckAuthFilter
from handlers.bot_config import bot
import asyncio

search_router = Router()


@search_router.callback_query(lambda cal: cal.data == "commands:search", CheckAuthFilter())
async def search_user(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id
    feed_api = UserFeedApi(user_id, token)

    data = await feed_api.get_users_from_form("6А")


    keyboard = get_pagination_keyboard(data, 0)
    await callback.message.answer(text="Список учеников данного класса:", reply_markup=keyboard)


@search_router.callback_query(lambda call: call.data.startswith("form"), CheckAuthFilter())
async def move_to_other_form(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id
    feed_api = UserFeedApi(user_id, token)

    key_offset = int(callback.data.split(":")[1])
    form = all_forms[key_offset]
    data = await feed_api.get_users_from_form(form)

    keyboard = get_pagination_keyboard(data, key_offset)

    await callback.message.edit_text(text="Список учеников данного класса:", reply_markup=keyboard)
    await callback.answer()


@search_router.callback_query(lambda call: call.data.startswith("pupil"), CheckAuthFilter())
async def get_pupil_profile(callback: CallbackQuery, token: str, is_admin: bool):
    user_id = callback.from_user.id
    cal_data = callback.data.split(":")

    form = cal_data[1]
    tg_id = cal_data[2]

    feed_api = UserFeedApi(user_id, token)

    data = await feed_api.get_users_from_form(form)

    pupil = data[tg_id]
    profile_text = (f"{pupil["first_name"]} {pupil["last_name"]} {form}\n\n"
                    f"{pupil["info"]}\n\n"
                    f"{pupil["karma"]} ❤")

    profile_photo = pupil["photo"]

    kb = user_card_action_kb(int(tg_id), is_admin, pupil["is_admin"])

    await callback.message.answer(text="Вот профиль данного пользователя:")
    await callback.message.answer_photo(photo=profile_photo, caption=profile_text, reply_markup=kb)


@search_router.callback_query(lambda cal: cal.data == "hide_profile")
async def hide_profile(callback: CallbackQuery):
    await callback.message.delete()

class FeedStates(StatesGroup):
    start = State()
    sex = State()
    form = State()
    watching = State()
    exchange = State()

@search_router.callback_query(lambda cal: cal.data == "commands:users_feed", CheckAuthFilter())
async def welcome_feed(callback: CallbackQuery, state: FSMContext):
    keyboard = [
        [InlineKeyboardButton(text="Поехали!", callback_data="Поехали!")]
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.answer("Это лента учеников нашей гимназии!\n Укажите параметры ленты перед тем как начать)", reply_markup=keyboard)
    await state.set_state(FeedStates.start)


@search_router.callback_query(lambda cal: cal.data == "Поехали!", StateFilter(FeedStates.start))
async def get_sex(callback: CallbackQuery, state: FSMContext):
    keyboard = get_sex_keyboard()
    await callback.message.answer(text="Ученики какого пола тебя интересуют?", reply_markup=keyboard)
    await state.set_state(FeedStates.sex)

@search_router.callback_query(lambda cal: cal.data in ("0", "1", "2"), StateFilter(FeedStates.sex))
async def get_form_more_than(callback: CallbackQuery, state: FSMContext):
    await state.update_data(sex=int(callback.data))

    keyboard = get_form_keyboard()
    await callback.message.answer(text="Выбери параллель(ученики из параллели ниже выбранной тебе попадаться не будут)", reply_markup=keyboard)
    await state.set_state(FeedStates.form)


@search_router.callback_query(lambda cal: cal.data in ("6", "7", "8", "9", "10", "11"), StateFilter(FeedStates.form), CheckAuthFilter())
async def start_watching(callback: CallbackQuery, state: FSMContext, token: str):
    user_id = callback.from_user.id
    form_min = int(callback.data)
    await state.update_data(form_min=form_min)
    sex = await state.get_value("sex")

    feed_api = UserFeedApi(user_id, token)
    pupil = await feed_api.get_user_from_feed(sex=sex, form_min=form_min, start=True)

    if not pupil:
        await callback.message.answer(text="К сожалению, не нашлось пользователей, удовлетворяющих данному фильтру(")
        await state.clear()
        return

    profile_text = (f"{pupil["first_name"]} {pupil["last_name"]} {pupil["form"]}\n\n"
                    f"{pupil["info"]}\n\n"
                    )

    profile_photo = pupil["photo"]
    keyboard = get_feed_keyboard(tg_id=pupil["tg_id"], karma=pupil["karma"])

    await callback.message.answer_photo(photo=profile_photo, caption=profile_text, reply_markup=keyboard)
    await state.set_state(FeedStates.watching)


@search_router.callback_query(lambda cal: cal.data in ("Далее", "Продолжить"), StateFilter(FeedStates.watching), CheckAuthFilter())
async def show_user_feed(callback: CallbackQuery, state: FSMContext, token: str):
    user_id = callback.from_user.id
    data = await state.get_data()
    feed_api = UserFeedApi(user_id, token)

    pupil = await feed_api.get_user_from_feed(sex=data["sex"], form_min=data["form_min"])

    profile_text = (f"{pupil["first_name"]} {pupil["last_name"]} {pupil["form"]}\n\n"
                    f"{pupil["info"]}\n\n"
                    )

    photo_id = pupil["photo"]
    keyboard = get_feed_keyboard(tg_id=pupil["tg_id"], karma=pupil["karma"])

    if callback.data == "Далее":
        profile_photo = InputMediaPhoto(media=photo_id, caption=profile_text)
        await callback.message.edit_media(media=profile_photo, reply_markup=keyboard)

    else:
        await callback.message.answer_photo(photo=photo_id, caption=profile_text, reply_markup=keyboard)


@search_router.callback_query(lambda cal: cal.data.startswith("karma"), StateFilter(FeedStates.watching), CheckAuthFilter())
async def increase_karma(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id
    call_data = callback.data.split(":")
    tg_id, karma = int(call_data[1]), int(call_data[2])

    feed_api = UserFeedApi(user_id, token)

    result = await feed_api.like_user(who_id=tg_id)

    if result:
        await callback.message.edit_caption(caption=callback.message.caption, reply_markup=get_feed_keyboard(tg_id, karma+1))
        await callback.answer()

    else:
        msg = await callback.message.answer(text="К сожалению Вы не можете так часто лайкать одного и того же пользователя(")
        await asyncio.sleep(3)
        await msg.delete()


@search_router.callback_query(lambda cal: cal.data.startswith("exchange"), CheckAuthFilter())
async def exchange_text_suggestion(callback: CallbackQuery, state: FSMContext):
    call_data = callback.data.split(":")
    receiver_id = int(call_data[1])
    from_state = call_data[2]

    user_id = callback.from_user.id
    feed_api = UserFeedApi(user_id)

    recently_sent = await feed_api.check_request_history(receiver_id=receiver_id)

    if recently_sent:
        msg = await callback.message.answer("Вы не можете так часто отправлять запрос в друзья(")
        await asyncio.sleep(3)
        await msg.delete()
        return

    await state.update_data(receiver_id=receiver_id, from_state=from_state)
    await callback.message.answer(text="Введи сообщение, которое увидит пользователь при просмотре твоей заявки:")

    await state.set_state(FeedStates.exchange)


@search_router.message(StateFilter(FeedStates.exchange))
async def send_exchange_message(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("Отправить можно только текст!")
        return

    data = await state.get_data()

    receiver_id = data["receiver_id"]
    from_state = data["from_state"]

    my_id = message.from_user.id
    my_username = message.from_user.username
    feed_api = UserFeedApi(my_id)

    await bot.send_message(chat_id=receiver_id, text="К тебе поступила заявка на обмен контактами, скорей узнай кто это")
    await feed_api.send_exchange_request(receiver_id=receiver_id, sender_username=my_username, message=message.text)


    if from_state == "feed":
        button = [[InlineKeyboardButton(text="Продолжить просмотр?", callback_data="Продолжить")]]
        keyboard = InlineKeyboardMarkup(inline_keyboard=button)
        await message.answer("Заявка отправлена!", reply_markup=keyboard)
        await state.set_state(FeedStates.watching)

    else:
        await message.answer("Заявка отправлена!")
        await state.clear()


@search_router.callback_query(lambda cal: cal.data == "commands:friend_requests", CheckAuthFilter())
async def info_about_requests(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id

    feed_api = UserFeedApi(user_id, token)
    amount = await feed_api.get_amount_requests()

    if amount == 0:
        await callback.message.answer("Пока что нет новых заявок(")
        return

    button = [[InlineKeyboardButton(text="Смотреть", callback_data="next_request")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button)

    await callback.message.answer(f"{amount} пользователей захотели обменяться с вами контактами", reply_markup=keyboard)


@search_router.callback_query(lambda cal: cal.data == "next_request")
async def get_request_info(callback: CallbackQuery):
    user_id = callback.from_user.id
    feed_api = UserFeedApi(user_id)

    info = await feed_api.get_requests()

    if not info:
        await callback.message.answer(text="Заявок больше нет")
        await callback.message.delete()
        return

    sender_id = info["sender_id"]
    sender_username = info["sender_username"]
    message = info["message"]

    keyboard = get_request_keyboard(sender_id, sender_username)

    auth_api = AuthApi(sender_id)
    auth_result = await auth_api.login()
    profile_api = UserProfileApi(sender_id, auth_result.token) # получаем данные о пользователе с помощью его access token

    pupil = await profile_api.get_profile()

    caption = f"{pupil["first_name"]} {pupil["last_name"]} {pupil["form"]} \n\n Сообщение Вам: \n {message}"
    photo = pupil["photo"]

    if not callback.message.photo:
        await callback.message.answer_photo(photo=photo, caption=caption, reply_markup=keyboard)

    else:
        photo = InputMediaPhoto(media=photo, caption=caption)
        await callback.message.edit_media(media=photo, reply_markup=keyboard)


@search_router.callback_query(lambda cal: cal.data.startswith("agree"))
async def agree_with_exchange(callback: CallbackQuery):
    cal_data = callback.data.split(":")

    pupil_id, pupil_username = int(cal_data[1]), cal_data[2]
    my_username = callback.from_user.username

    button = [[InlineKeyboardButton(text="Продолжить", callback_data="next_request")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button)

    await callback.message.answer(f"Успешно! Начинайте общение прямо сейчас: @{pupil_username}")
    await callback.message.answer(text="Или продолжите просмотр заявок:", reply_markup=keyboard)

    await bot.send_message(chat_id=pupil_id, text=f"Ваша заявка на обмен контактов была одобрена! @{my_username}")

















