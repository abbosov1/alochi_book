from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Telefon raqamingizni jo'natish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def teacher_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Kitobga buyurtma berish"), KeyboardButton(text="Mening ma'lumotlarim")],
            [KeyboardButton(text="Biz bilan bog'lanish"), KeyboardButton(text="Ma'lumotlarni o'zgartirish")],
        ],
        resize_keyboard=True
    )


def worker_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Buyurtma berish")]
        ],
        resize_keyboard=True
    )


def order_count_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="-", callback_data="order:count:decrease"),
                InlineKeyboardButton(text="+", callback_data="order:count:increase")
            ],
            [InlineKeyboardButton(text="Buyurtma berish", callback_data="order:count:submit")]
        ]
    )


def order_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha", callback_data="order:count_confirm:yes"),
                InlineKeyboardButton(text="Yo'q", callback_data="order:count_confirm:no")
            ]
        ]
    )


def school_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha", callback_data="order:school_confirm:yes"),
                InlineKeyboardButton(text="Yo'q", callback_data="order:school_confirm:no")
            ]
        ]
    )


def final_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Ha", callback_data="order:final_confirm:yes"),
                InlineKeyboardButton(text="Yo'q", callback_data="order:final_confirm:no")
            ]
        ]
    )
