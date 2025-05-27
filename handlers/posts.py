from aiogram import Router
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from .api.posts_api import PostsApi
from .api.gymcoins_api import GymcoinsApi
from .api.content_api import ContentApi
from .api.admin_api import AdminApi
from .settings import CheckAuthFilter
from .interface import get_post_keyboard, get_choose_post_type_kb, get_post_stat_kb, only_negative_kb
from decouple import config

posts_router = Router()

class PostCreateStates(StatesGroup):
    start_dialog = State()
    post_type = State()
    post_content = State()
    post_describe = State()


@posts_router.callback_query(lambda cal: cal.data == "commands:create_post", CheckAuthFilter())
async def post_create(callback: CallbackQuery, state: FSMContext):
    post_cost = config("POST_COST_CREATE")
    like_cost = int(config("LIKE_COST"))
    advance_cost = int(config("ADVANCE_CREATE"))


    text = ("Здесь вы можете создать пост! \n\n"
            "Тарифы:\n"        
            f"Стоимость поста типа текст/фото: {post_cost}💎\n"
            f"Стоимость поста типа голосовое/кружочек/видео: {advance_cost}💡\n"
            f"1❤ Вашему посту = {like_cost}💡")

    button = [[InlineKeyboardButton(text="Создать пост🔥", callback_data="create_post")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button, resize_keyboard=True)


    await callback.message.answer(text=text, reply_markup=keyboard)
    await state.set_state(PostCreateStates.start_dialog)


@posts_router.callback_query(lambda cal: cal.data == "create_post", CheckAuthFilter())
async def ask_content_type(callback: CallbackQuery, state: FSMContext, token: str):
    user_id = callback.from_user.id

    post_api = PostsApi(user_id, token)

    is_allowed = await post_api.allow_post()

    if not is_allowed:
        await callback.message.answer("Лимит постов на день исчерпан( Купите опцию доп поста или ждите до завтра.")
        return


    await callback.message.answer(text="Выбери тип поста:", reply_markup=get_choose_post_type_kb())
    await state.set_state(PostCreateStates.post_type)

@posts_router.callback_query(StateFilter(PostCreateStates.post_type))
async def get_content_type(callback: CallbackQuery, state: FSMContext):
    post_type = callback.data

    answers = {
                "text": "Отправь текст поста:",
                "text_photo": "Отправь фото с текстом или просто фото:",
                "voice": "Отправь голосовое сообщение:",
                "circle": "Отправь кружочек:",
                "video": "Отправь мне видео и текст к нему(по желанию):"
            }


    await state.update_data(type=post_type)
    await callback.message.answer(text=answers[post_type])
    await state.set_state(PostCreateStates.post_content)


@posts_router.message(StateFilter(PostCreateStates.post_content))
async def get_content(message: Message, state: FSMContext):
    content_type = (await state.get_data())["type"]

    if content_type == "text":
        if not message.text:
            await message.answer("Пришли мне только текст!")
            return

        await state.update_data(text=message.text, content="")

    elif content_type == "text_photo":
        if not message.photo:
            await message.answer("Пришли мне фото!")
            return

        photo_id = message.photo[-1].file_id
        caption = message.caption if message.caption else ""

        await state.update_data(content=photo_id, text=caption)

    elif content_type == "voice":
        if not message.voice:
            await message.answer("Пришли мне голосовое!")
            return

        voice_id = message.voice.file_id
        await state.update_data(content=voice_id, text="")



    elif content_type == "circle":
        if not message.video_note:
            await message.answer("Пришли мне кружочек!")
            return

        video_note_id = message.video_note.file_id
        await state.update_data(content=video_note_id, text="")

    elif content_type == "video":
        if not message.video:
            await message.answer("Пришли мне видео!")
            return

        video = message.video
        video_id = video.file_id
        caption = message.caption if message.caption else ""
        await state.update_data(content=video_id, text=caption)

    await message.answer(text="Теперь введи краткое описание поста. \n"
                              "Это позволит Вам понять о каком посте идёт речь при просмотре статистики")

    await state.set_state(PostCreateStates.post_describe)


@posts_router.message(StateFilter(PostCreateStates.post_describe), CheckAuthFilter())
async def get_post_describe(message: Message, state: FSMContext, token: str):
    user_id = message.from_user.id
    post_api = PostsApi(user_id, token)
    gymcoins_api = GymcoinsApi(user_id, token)

    if not message.text:
        await message.answer("Отправь текст!")
        return

    if len(message.text) > 20:
        await message.answer("Слишком длинное описание!")
        return

    data = await state.get_data()

    describe = message.text
    text = data["text"]
    content = data["content"]
    type = data["type"]


    if type in ("voice", "circle", "video"):
        advance = True

    else:
        advance = False

    pay_result = await post_api.pay_for_post(advance=advance)

    if pay_result.success is False:
        ico = "💡" if advance else "💎"
        await message.answer(f"Недостаточно средств, чтобы опубликовать пост! Не хватает: {pay_result.amount}{ico}")
        await state.clear()
        return


    result = await post_api.create_post_db(text=text, content=content, describe=describe, type=type)

    if not result:
        await message.answer("Что то пошло не так(")
        await gymcoins_api.withdraw_funds(pay_result.amount, source="bank") # возвращаем средства если пост не опубликовался
        await state.clear()
        return

    await message.answer(text="Пост успешно создан и опубликован!")
    await state.clear()


@posts_router.callback_query(lambda cal: cal.data == "commands:posts", CheckAuthFilter())
async def start_post_feed(callback: CallbackQuery, is_admin: bool):
    user_id = callback.from_user.id
    posts_api = PostsApi(user_id)

    await posts_api.delete_posts_in_cache() # удаляем старые посты из кэша

    if is_admin:
        kb = only_negative_kb()
        await callback.message.answer("Какие посты тебе показать:", reply_markup=kb)
        return

    button = [[InlineKeyboardButton(text="Начать", callback_data="next_post")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button)


    text = "Добро пожаловать в ленту новостей нашей Гимназии!"

    await callback.message.answer(text=text, reply_markup=keyboard)



@posts_router.callback_query(lambda cal: cal.data.startswith("negative"))
async def apply_toxicity(callback: CallbackQuery):
    admin_id = callback.from_user.id
    admin_api = AdminApi(admin_id)

    only_negative = callback.data.split(":")[1]

    if only_negative == "yes":
        value = True

    else:
        value = False

    await admin_api.set_only_negative(value=value)


    button = [[InlineKeyboardButton(text="Начать", callback_data="next_post")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button)

    await callback.message.answer(text="Начать просмотр:", reply_markup=keyboard)


@posts_router.callback_query(lambda cal: cal.data == "next_post" or  cal.data.startswith("like") or cal.data.startswith("dislike"), CheckAuthFilter())
async def get_post(callback: CallbackQuery, token: str, is_admin: bool):
    user_id = callback.from_user.id

    post_api = PostsApi(user_id, token)

    if callback.data != "next_post":
        cal_data = callback.data.split(":")
        action = cal_data[0] # ❤ или 👎
        post_id = int(cal_data[1])
        creator_id = cal_data[4]
        post_type = cal_data[5]

        result = await post_api.post_action(post_id=post_id, action=action, creator_id=creator_id)

        if result:
            likes = int(cal_data[2])
            dislikes = int(cal_data[3])

            if action == "like":
                likes += 1
            else:
                dislikes += 1

            keyboard = get_post_keyboard(likes, dislikes, post_id, creator_id, post_type, is_admin)

            await callback.message.edit_reply_markup(caption=callback.message.caption, reply_markup=keyboard)

    only_negative = 0

    if is_admin:
        admin_api = AdminApi(user_id)
        only_negative = await admin_api.only_negative()

    post_data = await post_api.watch_post(only_negative)

    if not post_data:
        await callback.message.answer("Нет новых постов(")
        return


    post_id = post_data["post_id"]
    content = post_data["content"]
    post_text = post_data["text"]
    likes = post_data["likes"]
    dislikes = post_data["dislikes"]
    creator_id = post_data["creator_id"]
    post_type = post_data["type"]
    toxicity = post_data["toxicity"]

    translate_toxicity = {
        "dangerous": "Провокация",
        "obscenity": "Непристойность",
        "insult": "Оскорбление",
        "threat": "Угроза",
        "non-toxic": "Нейтральность"
    }

    keyboard = get_post_keyboard(likes, dislikes, post_id, creator_id, post_type, is_admin)

    label = translate_toxicity[toxicity] if toxicity else "Не определено"

    if is_admin:
        post_text = post_text + "\n" + f"Метка: {label}" # вывод метки токсичности для админов

    if post_type == "text":
        await callback.message.answer(text=post_text, reply_markup=keyboard)

    elif post_type == "text_photo":
        await callback.message.answer_photo(photo=content, caption=post_text, reply_markup=keyboard)

    elif post_type == "voice":
        await callback.message.answer_voice(voice=content, reply_markup=keyboard)

    elif post_type == "circle":
        await callback.message.answer_video_note(video_note=content, reply_markup=keyboard)

    else:
        await callback.message.answer_video(video=content, caption=post_text, reply_markup=keyboard)


@posts_router.callback_query(lambda cal: cal.data == "commands:stat", CheckAuthFilter())
async def stat_next_post(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id

    post_api = PostsApi(user_id, token)
    data = await post_api.load_post_stat()

    limit = data["count"]

    if limit == 0:
        await callback.message.answer(text="Нет активных постов.")
        return

    btn = [[InlineKeyboardButton(text="Смотреть статиcтику", callback_data=f"stat:0:{limit}")]]
    kb = InlineKeyboardMarkup(inline_keyboard=btn)

    text = "Продолжить просмотр статистики:" if callback.message.reply_markup.inline_keyboard[0][0].text == "Далее" else "Здесь ты можешь посмотреть статистику своих постов."

    await callback.message.answer(text=text, reply_markup=kb)



@posts_router.callback_query(lambda cal: cal.data.startswith("stat"))
async def get_stat(callback: CallbackQuery):
    user_id = callback.from_user.id
    cal_data = callback.data.split(":")

    offset = int(cal_data[1])
    limit = int(cal_data[2])

    post_api = PostsApi(user_id)

    post_data = await post_api.get_post_stat(offset=offset)

    post_types = {"text": "текст", "text_photo": "текст+фото", "voice": "голосовое", "circle": "кружочек", "video": "видео"}

    post_id = post_data["post_id"]
    describe = post_data["describe"]
    post_type = post_types[post_data["type"]]
    likes = post_data["likes"]
    dislikes = post_data["dislikes"]

    stat_text = f"Описание поста: {describe} \nТип поста: {post_type} \n\n ❤: {likes} \n 👎: {dislikes}"

    stat = await ContentApi.allow_content(user_id, "stat")

    keyboard = get_post_stat_kb(post_id=post_id, offset=offset+1, limit=limit, stat=stat)

    await callback.message.edit_text(text=stat_text, reply_markup=keyboard)


@posts_router.callback_query(lambda cal: cal.data.startswith("user_delete_post"), CheckAuthFilter())
async def delete_post_user(callback: CallbackQuery, token: str):
    post_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    post_api = PostsApi(user_id, token=token)
    delete_result = await post_api.delete_post(post_id)

    btn = [[InlineKeyboardButton(text="Далее", callback_data="commands:stat")]]
    kb = InlineKeyboardMarkup(inline_keyboard=btn)

    if delete_result:
        await callback.message.edit_text("Пост успешно удалён✅", reply_markup=kb)

    else:
        await callback.message.answer("Ошибка! Не могу удалить пост❌")


@posts_router.callback_query(lambda cal: cal.data.startswith("list_likers"), CheckAuthFilter())
async def get_likers_list(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id
    post_id = int(callback.data.split(":")[1])

    post_api = PostsApi(user_id, token)

    data = await post_api.get_pupil_liked_post(post_id=post_id)

    if not data:
        return

    buffer = ""

    for pupil in data:
        buffer += f"{pupil["first_name"]} {pupil["last_name"]}, {pupil["form"]}"


    if buffer:
        await callback.message.answer_document(
            BufferedInputFile(buffer.encode(), "stat.txt")
        )


