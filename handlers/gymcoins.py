from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
)
from decouple import config
from .api.gymcoins_api import GymcoinsApi
from .interface import get_funds_keyboard
from .settings import CheckAuthFilter

gymcoins_router = Router()


@gymcoins_router.callback_query(lambda cal: cal.data == "commands:wallet", CheckAuthFilter())
async def welcome_funds(callback: CallbackQuery):
    keyboard = get_funds_keyboard()
    await callback.message.answer(text="Здесь вы можете выполнить основные операции с Вашими gymcoins!", reply_markup=keyboard)


@gymcoins_router.callback_query(lambda cal: cal.data == "balance", CheckAuthFilter())
async def get_my_balance(callback: CallbackQuery, token: str):
    user_id = callback.from_user.id

    gymcoins_api = GymcoinsApi(user_id, token)

    balance = await gymcoins_api.get_balance()

    if balance is False:
        await callback.message.answer("Не могу посчитать средства(")
        return

    await callback.message.answer(f"Баланс: {balance} 💎")

class WithdrawalStates(StatesGroup):
    withdraw = State()

@gymcoins_router.callback_query(lambda cal: cal.data == "author_wallet")
async def get_author_wallet(callback: CallbackQuery):
    user_id = callback.from_user.id
    gymcoins_api = GymcoinsApi(user_id)

    profit = await gymcoins_api.get_profit()

    if profit == 0:
        await callback.message.answer(text="Доступно к выводу: 0💡")
        return

    button = [[InlineKeyboardButton(text="Вывести 💡->💎", callback_data="вывести")]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=button)

    await callback.message.answer(text=f"Доcтупно к выводу: {profit}💡", reply_markup=keyboard)



@gymcoins_router.callback_query(lambda cal: cal.data.startswith("вывести"))
async def get_sum_withdraw(callback: CallbackQuery, state: FSMContext):
    button = [[InlineKeyboardButton(text="Отменить вывод", callback_data="cancel_withdraw")]]
    kb = InlineKeyboardMarkup(inline_keyboard=button)

    await callback.message.answer(text="❗ Дополнительные опции можно купить ТОЛЬКО за 💡, а не 💎!"
                                       " Так что будьте до конца уверены перед тем, как выводить 💡 на общий баланс.", reply_markup=kb)
    await callback.message.answer(text="Введи сумму, которую хочешь вывести:")
    await state.set_state(WithdrawalStates.withdraw)


@gymcoins_router.callback_query(lambda cal: cal.data == "cancel_withdraw")
async def cancel_withdraw(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(text="Отменяю процесс.")
    await state.clear()

@gymcoins_router.message(StateFilter(WithdrawalStates.withdraw), CheckAuthFilter())
async def withdraw_profit(message: Message, state: FSMContext, token: str):
    if not message.text.isdigit():
        await message.answer("Введи число!")
        return

    amount = int(message.text)

    user_id = message.from_user.id
    gymcoins_api = GymcoinsApi(user_id, token)

    result = await gymcoins_api.withdraw_funds(amount, "profit")

    if result:
        await message.answer("Успешно!")

    else:
        await message.answer("Недостаточно средств к выводу!")

    await state.clear()

@gymcoins_router.callback_query(lambda cal: cal.data == "explain")
async def explain_balances(callback: CallbackQuery):
    text = ("Работает это так: \n\n"
            "Вы тапаете Gymcoins💎, они отправляются на основной баланс(Баланс)."
            "Средства с основного баланса расходуются на создание новых постов. \n\n"
            "Средства в кошельке автора💡 - это те средства, которые заработали для Вас Ваши посты(лайки)."
            "Их Вы можете потратить на покупку опций, а также на создание гс и кружочков."
            "Средства из кошелька автора можно вывести на основной баланс, однако наоборот сделать не получится.")

    await callback.message.answer(text=text)


@gymcoins_router.callback_query(lambda cal: cal.data == "commands:maining", CheckAuthFilter())
async def start_app(callback: CallbackQuery):
    text = ("Начинайте майнить прямо сейчас, но учтите, что: \n"
            "❗ При закрытии страницы счётчик gymcoins обнуляется, так что не забывайте выводить их на баланс(save) после сессии майнинга. \n"
            "❗ Мин сумма вывода за РАЗ = 100 gymcoins, макс = 10000")

    btn = [[InlineKeyboardButton(text="майнить💎", web_app=WebAppInfo(url=f'{config("APP_URL")}/gymcoins'))]]
    keyboard = InlineKeyboardMarkup(inline_keyboard=btn)

    await callback.message.answer(text=text, reply_markup=keyboard)
