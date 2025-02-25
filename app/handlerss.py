from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from app.datebase import *
from app.keyboards import register_keyboard, phone_keyb

from app.middlewheres import TestMiddlewhere


router = Router()

router.message.outer_middleware(TestMiddlewhere())

SERVANTS = ()


class Register(StatesGroup):
    school = State()
    name = State()
    number = State()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Assalomu alaykum botga xush kelibsiz!\n"
        "Botdan to'liq foydalanish uchun registratsiyadan o'ting",
        reply_markup=register_keyboard
    )


@router.message(F.text == "Registratsiyadan o'tish")
async def register_btn(message: Message, state: FSMContext):
    await message.answer("Telefon raqamingizni jo'nating", reply_markup=phone_keyb)
    await state.set_state(Register.number)


@router.message(Register.number)
async def phone_received(message: Message, state: FSMContext):
    user_id = message.from_user.id
    phone_number = message.contact.phone_number
    cursor.execute("UPDATE user SET phone = ? WHERE user_id = ?", (phone_number, user_id))
    conn.commit()
    if user_id in SERVANTS:
        pass
    else:
        await message.answer("Raqam qabul qilindi!\n"
                             "Endi ismingizni kiriting!")
        await state.set_state(Register.name)


@router.message(Register.name)
async def get_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text
    cursor.execute("UPDATE user SET fullname = ? WHERE user_id = ?", (name, user_id))
    conn.commit()
    await message.answer(f"Endi qaysi maktabda ishlashingizni kiriting")
    await state.set_state(Register.school)


@router.message(Register.school)
async def get_photo(message: Message):
    user_id = message.from_user.id
    school_number = message.text
    cursor.execute("UPDATE user SET school_number = ? WHERE user_id = ?", (school_number, user_id))
    conn.commit()
    await message.answer("Siz muvaffaqiyatli tarzda registratsiyadan o'tdingiz")