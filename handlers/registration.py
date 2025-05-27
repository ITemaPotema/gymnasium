from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from decouple import config
from .api.auth_api import AuthApi, ProfileStatus, CreateStatus
from .api.profile_api import UserProfileApi, ProfileProgress
from .interface import edit_profile_kb, get_grade_kb, get_letter_kb
from .settings import CheckAuthFilter

registration_router = Router()

class Profile(StatesGroup):
    grade = State()
    letter = State()
    photo = State()
    info = State()


class IPhoneAuthStates(StatesGroup):
    vk_id = State()


@registration_router.message(Command("authorization"))
async def start_authorization(message: Message):
    buttons = [
            [InlineKeyboardButton(text="IOS(IPhone)", callback_data="system:iphone")],
            [InlineKeyboardButton(text="Android", callback_data="system:android")]
        ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    await message.answer(text="Выбери ОС твоего телефона:", reply_markup=keyboard)

@registration_router.callback_query(lambda cal: cal.data.startswith("system"))
async def authorization(callback: CallbackQuery, state: FSMContext):
    system = callback.data.split(":")[1]

    if system == "android":
        reg_but = InlineKeyboardButton(text="Авторизоваться", web_app=WebAppInfo(url=f'{config("APP_URL")}/welcome_authorization'))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[reg_but]])

        await callback.message.answer("Авторизуйся через ВК", reply_markup=keyboard)

    else:
        await callback.message.answer(text="Отправь своё VK ID.\n"
                                           "Его ты можешь найти в настройкак своего VK профиля\n"
                                           "https://id.vk.com/account/#/main\n\n"                                           
                                           "P.S: VK ID не являентся приватной информацией,"
                                           " любой пользователь может узнать твой id даже через браузер")

        await state.set_state(IPhoneAuthStates.vk_id)


@registration_router.message(StateFilter(IPhoneAuthStates.vk_id))
async def finish_auth_iphone(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer(text="Некорректный формат id!")
        return

    tg_name = message.from_user.username
    tg_id = message.from_user.id
    vk_id = int(message.text)

    auth_api = AuthApi(tg_id=tg_id)

    status_result = await auth_api.auth_iphone(tg_name=tg_name, vk_id=vk_id)

    if status_result == 200:
        await message.answer("Авторизация прошла успешно! Теперь создай свой профиль!(/personal))")

    elif status_result == 201:
        await message.answer("Пользователь уже авторизован!")

    else:
        await message.answer("Ошибка! Запустите процесс по новой!")

    await state.clear()


@registration_router.callback_query(lambda cal: cal.data == "commands:profile")
async def registration(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id

    auth_api = AuthApi(tg_id=user_id)
    auth_result = await auth_api.login()

    if auth_result.status == ProfileStatus.HAS_PROFILE:
        token = auth_result.token
        profile_api = UserProfileApi(tg_id=user_id, token=token)

        profile = await profile_api.get_profile()

        if not profile:
            await callback.message.answer("Ошибка! Не могу загрузить профиль!")
            return

        await callback.message.answer("Твой профиль выглядит следующим образом:")
        await callback.message.answer_photo(profile["photo"],
                                    caption=f"{profile["first_name"]} {profile["last_name"]} {profile["form"]} \n\n"
                                            f"{profile["info"]} \n\n"
                                            f"{profile["karma"]} ❤")
        return

    progress = ProfileProgress(user_id)

    saved_progress_data = await progress.get_profile_progress() # сохранённые данные профиля пользователя, которые нужно сохранить в бд после авторизации

    if saved_progress_data:
        result = await auth_api.create_profile(saved_progress_data)
        print(result.status)

        if result.status == CreateStatus.SUCCESS:
            await callback.message.answer("Профиль успешно создан! Чтобы перейти в него, нажмите на кнопку 'Профиль' ещё раз.")
            return

        if result.status == CreateStatus.NOT_AUTHENTICATED:
            await callback.message.answer("Авторизуйтесь, чтобы завершить процесс создания профиля!(/authorization)")
            return

    keyboard = get_grade_kb()
    await callback.message.answer("Приступим к оформлению твоего профиля!\n Выбери параллель, в которой ты учишься:", reply_markup=keyboard)

    await state.update_data(tg_id=callback.from_user.id)
    await state.set_state(Profile.grade)


@registration_router.callback_query(StateFilter(Profile.grade), lambda cal: cal.data.startswith("grade"))
async def get_user_grade(callback: CallbackQuery, state: FSMContext):
    grade = callback.data.split(":")[1]

    kb = get_letter_kb(grade)

    await callback.message.answer(text="Выбери букву твоего класса:", reply_markup=kb)
    await state.set_state(Profile.letter)


@registration_router.callback_query(StateFilter(Profile.letter), lambda cal: cal.data.startswith("grade_letter"))
async def get_user_letter(callback: CallbackQuery, state: FSMContext):
    form = callback.data.split(":")[1]

    await state.update_data(form=form)

    await callback.message.answer(text="Отправь мне фото-аватарку, которая будет видна всеми пользователям.\n"
                         "Было бы очень здорово, если бы на фото был действительно ты, ведь цель этой платформы открытое общение!")

    await state.set_state(Profile.photo)



@registration_router.message(StateFilter(Profile.photo))
async def handle_avatar(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("Отправь мне фото!")
        return

    ava = message.photo[-1]
    ava_id = ava.file_id

    await state.update_data(photo=ava_id)
    await state.set_state(Profile.info)
    await message.answer("Теперь расскажи подробней о себе в целом: \n привычках, хобби, жизненной позиции")


@registration_router.message(StateFilter(Profile.info))
async def get_user_info(message: Message, state: FSMContext):
    text = message.text
    user_id = message.from_user.id

    if len(text) < 20:
        await message.answer("Слишком мало, расскажи побольше)")
        return

    elif len(text) > 700:
        await message.answer("Слишком длинное описание, чуть чуть подсократи.")
        return

    await state.update_data(info=text)

    try:
        auth_api = AuthApi(user_id)
        user_data = await state.get_data()
        result = await auth_api.create_profile(user_data)

        if result.status == CreateStatus.SUCCESS:
            await message.answer("Профиль успешно создан!")

        if result.status == CreateStatus.NOT_AUTHENTICATED:
            user_id = message.from_user.id
            await message.answer("Кажется ты забыл авторизоваться! Я сохранил настройки твоего профиля,"
                                 "он создастся, как только ты авторизуешься.(/authorization)")

            progress = ProfileProgress(user_id)
            await progress.save_profile_progress(user_data) # сохраняем данные до того момента пока пользователь не авторизуется и только потом создаём профиль

    except Exception as e:
        print(e)
        await message.answer("Непредвиденная ошибка! Попробуйте создать профиль ещё раз.")

    finally:
        await state.clear()


@registration_router.callback_query(lambda cal: cal.data == "commands:edit_profile", CheckAuthFilter())
async def start_edit_profile(callback: CallbackQuery):
    keyboard = edit_profile_kb()
    await callback.message.answer(text="Выбери то, что собираешься редактировать:", reply_markup=keyboard)

class EditStates(StatesGroup):
    photo = State()
    info = State()

@registration_router.callback_query(lambda cal: cal.data.startswith("edit"))
async def choose_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[1]

    if category == "photo":
        await callback.message.answer(text="Пришли мне новое фото:")
        await state.set_state(EditStates.photo)

    else:
        await callback.message.answer(text="Пришли мне новое описание:")
        await state.set_state(EditStates.info)


@registration_router.message(StateFilter(EditStates.photo), CheckAuthFilter())
async def edit_photo(message: Message, state: FSMContext, token: str):
    if not message.photo:
        await message.answer("Пришли мне фото!")
        return

    user_id = message.from_user.id
    profile_api = UserProfileApi(user_id, token)

    new_photo = message.photo[-1]
    data = new_photo.file_id

    result = await profile_api.edit_profile(data, category="photo")

    if result:
        await message.answer(text="Фото обновлено!")
        await state.clear()


@registration_router.message(StateFilter(EditStates.info), CheckAuthFilter())
async def edit_info(message: Message, state: FSMContext, token: str):
    if not message.text:
        await message.answer("Пришли мне текст!")
        return

    data = message.text

    if len(data) < 20:
        await message.answer("Слишком мало, расскажи побольше)")
        return

    elif len(data) > 700:
        await message.answer("Слишком длинное описание, чуть чуть подсократи.")
        return

    user_id = message.from_user.id

    profile_api = UserProfileApi(user_id, token)

    result = await profile_api.edit_profile(data, category="info")

    if result:
        await message.answer(text="Описание обновлено!")
        await state.clear()


@registration_router.message(Command("deactivate"), CheckAuthFilter())
async def deactivate_warning(message: Message):
    text = ("❗ Ваш профиль будет удалён, но авторизационные данные останутся,"
            "так что Вы сможете в любой момент заново его создать.")

    btn = [[InlineKeyboardButton(text="Отключить профиль", callback_data="profile:deactivate")]]
    kb = InlineKeyboardMarkup(inline_keyboard=btn)

    await message.answer(text=text, reply_markup=kb)


@registration_router.callback_query(lambda cal: cal.data == "profile:deactivate", CheckAuthFilter())
async def profile_deactivate(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id

    profile_api = UserProfileApi(user_id, token)

    deactivate_result = await profile_api.deactivate_profile()

    if deactivate_result:
        await callback.message.answer(text="Профиль отключён! Скорее возвращайся!❤🙏")

    else:
        await callback.message.answer(text="Ошибка! Не могу отключить твой профиль!")