from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from decouple import config
from .settings import all_forms


def get_grade_kb():
    keyboard = InlineKeyboardBuilder()

    for grade in range(6, 12):
        keyboard.add(
            InlineKeyboardButton(text=str(grade), callback_data=f"grade:{grade}"),
        )

    keyboard.adjust(3)
    return keyboard.as_markup()


def get_letter_kb(grade):
    keyboard = InlineKeyboardBuilder()


    forms_letters = {
        "6": ("А", "Б", "В", "Г"),
        "7": ("А", "Б", "В", "Г", "Д"),
        "8": ("А", "Б", "В", "Д"),
        "9": ("А", "Б", "В", "Г"),
        "10": ("А", "Б", "В", "Г"),
        "11": ("А", "Б")
    }

    letters = forms_letters[grade]

    for letter in letters:
        keyboard.add(
            InlineKeyboardButton(text=letter, callback_data=f"grade_letter:{grade}{letter}"),
        )

    keyboard.adjust(3)
    return keyboard.as_markup()


def get_pagination_keyboard(data: dict, key_offset: int) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardBuilder()
    forms = all_forms
    form = forms[key_offset]


    keyboard.add(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"form:{key_offset - 1}"),
        InlineKeyboardButton(text=form, callback_data="current_page"),
        InlineKeyboardButton(text="Вперед ➡️", callback_data=f"form:{(key_offset + 1) % len(forms)}")
    )

    if not data:
        keyboard.add(InlineKeyboardButton(text="пусто", callback_data="empty"))

    else:
        for tg_id in data:
            pupil = data[tg_id]
            keyboard.add(InlineKeyboardButton(text=f"{pupil['first_name']} {pupil['last_name']}", callback_data=f"pupil:{form}:{tg_id}"))

    keyboard.adjust(3, 2)
    return keyboard.as_markup()


def get_sex_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
    InlineKeyboardButton(text="Мужской", callback_data="2"),
        InlineKeyboardButton(text="Женский", callback_data="1"),
        InlineKeyboardButton(text="Не важно", callback_data="0")
    )

    keyboard.adjust(2)
    return keyboard.as_markup()


def get_form_keyboard():
    keyboard = InlineKeyboardBuilder()
    btns = []

    for i in range(6, 12):
        btns.append(InlineKeyboardButton(text=str(i), callback_data=str(i)))

    keyboard.add(*btns)

    keyboard.adjust(3)
    return keyboard.as_markup()


def get_feed_keyboard(tg_id: int, karma: int):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Обменяться контактами", callback_data=f"exchange:{tg_id}:feed"),
        InlineKeyboardButton(text=f"{str(karma)} ❤", callback_data=f"karma:{tg_id}:{karma}"),
        InlineKeyboardButton(text="Далее", callback_data="Далее")
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_request_keyboard(sender_id, sender_username):
    buttons = [
        [
            InlineKeyboardButton(text="Обменяться", callback_data=f"agree:{sender_id}:{sender_username}"),
            InlineKeyboardButton(text="Отказаться", callback_data="next_request")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_post_keyboard(likes, dislikes, post_id, creator_id, post_type, is_admin):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text=f"{likes} ❤", callback_data=f"like:{post_id}:{likes}:{dislikes}:{creator_id}:{post_type}"),
        InlineKeyboardButton(text=f"{dislikes} 👎", callback_data=f"dislike:{post_id}:{likes}:{dislikes}:{creator_id}:{post_type}"),
    )

    if is_admin:
        keyboard.add(InlineKeyboardButton(text="Удалить пост🛑", callback_data=f"admin:delete_post:{post_id}:{creator_id}"))

    keyboard.adjust(2)
    return keyboard.as_markup()


def get_funds_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Баланс💎", callback_data="balance"),
        InlineKeyboardButton(text=f"Кошелёк автора👛", callback_data=f"author_wallet"),
        InlineKeyboardButton(text="В чём отличие?", callback_data="explain")
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_choose_post_type_kb():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="текст", callback_data="text"),
        InlineKeyboardButton(text="текст+фото", callback_data="text_photo"),
        InlineKeyboardButton(text="голосовое", callback_data="voice"),
        InlineKeyboardButton(text="кружочек", callback_data="circle"),
        InlineKeyboardButton(text="видео", callback_data="video")
    )

    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()


def get_post_stat_kb(post_id, offset, limit, stat):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Далее", callback_data=f"stat:{offset % limit}:{limit}"),
        InlineKeyboardButton(text="Удалить пост❌", callback_data=f"user_delete_post:{post_id}")
    )

    if stat:
        keyboard.add(InlineKeyboardButton(text="Кто лайкнул?", callback_data=f"list_likers:{post_id}"))

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_stars_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Оплатить 100 ⭐️", pay=True)

    return builder.as_markup()


def edit_profile_kb():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Фото📷", callback_data="edit:photo"),
        InlineKeyboardButton(text="Инфо✏", callback_data="edit:info")
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_options_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Доп пост➕1️⃣", callback_data="option:extra_post"),
        InlineKeyboardButton(text="Пост-лайки", callback_data="option:stat")
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_support_keyboard():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Stars⭐️", callback_data="support:stars"),
        InlineKeyboardButton(text="По номеру карты", callback_data="support:credit_card")
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_profile_commands():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Профиль😎", callback_data="commands:profile"),
        InlineKeyboardButton(text="Редактировать✏", callback_data="commands:edit_profile"),
        InlineKeyboardButton(text="Заявки💌", callback_data="commands:friend_requests"),
        InlineKeyboardButton(text="Кошелёк👛", callback_data="commands:wallet"),
    )

    keyboard.adjust(2, 1, 1)
    return keyboard.as_markup()


def get_search_commands():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Поиск🔍", callback_data="commands:search"),
        InlineKeyboardButton(text="Лента🎞", callback_data="commands:users_feed"),
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_post_commands():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Создать🔥", callback_data="commands:create_post"),
        InlineKeyboardButton(text="Лента🎞", callback_data="commands:posts"),
        InlineKeyboardButton(text="Статистика📒", callback_data="commands:stat"),
        InlineKeyboardButton(text="Опции📈", callback_data="commands:options"),
        InlineKeyboardButton(text="Майнинг💎", callback_data="commands:maining")
    )

    keyboard.adjust(2, 2, 1)
    return keyboard.as_markup()


def get_chat_kb(online):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text=f"Онлайн🟩 {online}", callback_data="online"),
        InlineKeyboardButton(text="Поиск собеседника🔍", callback_data="chat:search"),
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def get_cancel_kb():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Отменить", callback_data="chat:cancel"),
    )

    keyboard.adjust()
    return keyboard.as_markup()


def only_negative_kb():
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
        InlineKeyboardButton(text="Только негативные", callback_data="negative:yes"),
        InlineKeyboardButton(text="Любые", callback_data="negative:no")
    )

    keyboard.adjust(1)
    return keyboard.as_markup()


def user_card_action_kb(tg_id: int, is_admin: bool, user_is_admin: bool):
    keyboard = InlineKeyboardBuilder()

    keyboard.add(
    InlineKeyboardButton(text="Обменяться контактами", callback_data=f"exchange:{tg_id}:search"),
            InlineKeyboardButton(text="Скрыть", callback_data="hide_profile"))

    if is_admin:
        if user_is_admin:
            promotion_text = "Исключить из админов❌"
            action = "downgrade"

        else:
            promotion_text = "Сделать админом✅"
            action = "upgrade"

        keyboard.add(
            InlineKeyboardButton(text=promotion_text, callback_data=f"promotion:{tg_id}:{action}"),
            InlineKeyboardButton(text="Забанить🚫", callback_data=f"admin:ban_user:{tg_id}")
        )

    keyboard.adjust(1)
    return keyboard.as_markup()