import logging

from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
)

from app import config, database, keyboards

router = Router()
logger = logging.getLogger(__name__)

# Глобальный словарь для хранения ожидаемых заказов от админа
admin_pending_orders = {}


# ============================================================================
# Регистрация (FSM)
# ============================================================================
class Registration(StatesGroup):
    waiting_for_contact = State()
    waiting_for_name = State()
    waiting_for_school = State()


@router.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.clear()
    if await database.user_exists(user_id):
        if user_id in config.WORKER_IDS:
            await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.\n:",
                                 reply_markup=keyboards.worker_menu_keyboard())
        elif user_id == config.ADMIN_ID:
            await message.answer("Xush kelibsiz admin. Siz ro'yxatdan o'tgansiz.", reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("Siz allaqachon ro'yxatdan o'tgansiz.\nMenyu:",
                                 reply_markup=keyboards.teacher_menu_keyboard())
        return
    await state.set_state(Registration.waiting_for_contact) 
    await message.answer("Assalomu alaykum botga xush kelibsiz!\nTelefon raqamingizni yuboring",
                         reply_markup=keyboards.contact_keyboard())


@router.message(Registration.waiting_for_contact, F.contact)
async def contact_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = message.contact.phone_number
    await database.add_user(user_id, phone=phone)
    await state.set_state(Registration.waiting_for_name)
    await message.answer("Sizning raqamingiz tasdiqlandi, endi ismingizni kiriting!",
                         reply_markup=ReplyKeyboardRemove())


@router.message(Registration.waiting_for_name)
async def name_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    name = message.text
    await database.update_user(user_id, name=name)
    await state.set_state(Registration.waiting_for_school)
    await message.answer("Endi qaysi maktabda ishlashingizni kiriting")


@router.message(Registration.waiting_for_school)
async def school_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    school = message.text
    await database.update_user(user_id, school=school)
    await message.answer("Ro'yxatdan o'tish yakunlandi, botdan foydalanishingiz mumkin!",
                         reply_markup=keyboards.teacher_menu_keyboard())
    await state.clear()


# ============================================================================
# Просмотр и изменение данных (для учителей)
# ============================================================================
@router.message(lambda message: message.text == "Mening ma'lumotlarim")
async def my_info_handler(message: types.Message):
    user_id = message.from_user.id
    user_info = await database.get_user(user_id)
    if user_info:
        teacher_id, phone, name, school = user_info
        info_text = (
            f"O'qtuvchi ma'lumotlari:\n"
            f"Ism: {name}\n"
            f"Telefon: {phone}\n"
            f"Maktab: {school if school else 'Noma\'lum'}"
        )
        await message.answer(info_text, reply_markup=keyboards.teacher_menu_keyboard())
    else:
        await message.answer("Ma'lumot topilmadi.")


class UpdateTeacherInfo(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_school = State()


@router.message(lambda message: message.text == "Ma'lumotlarni o'zgartirish")
async def update_info_start(message: types.Message, state: FSMContext):
    await state.set_state(UpdateTeacherInfo.waiting_for_new_name)
    await message.answer("Ismingizni qaytatdan kiriting:", reply_markup=ReplyKeyboardRemove())


@router.message(UpdateTeacherInfo.waiting_for_new_name)
async def update_info_name(message: types.Message, state: FSMContext):
    new_name = message.text
    await state.update_data(new_name=new_name)
    await state.set_state(UpdateTeacherInfo.waiting_for_new_school)
    await message.answer("Maktabingizni qaytatdan kiriting:")


@router.message(UpdateTeacherInfo.waiting_for_new_school)
async def update_info_school(message: types.Message, state: FSMContext):
    new_school = message.text
    data = await state.get_data()
    new_name = data.get("new_name")
    user_id = message.from_user.id
    await database.update_user(user_id, name=new_name, school=new_school)
    await message.answer("Ma'lumotlaringiz muvaffaqiyatli yangilandi.", reply_markup=keyboards.teacher_menu_keyboard())
    await state.clear()


@router.message(lambda message: message.text == "Biz bilan bog'lanish")
async def contact_admin_handler(message: types.Message):
    await message.answer(f"Admin bilan bog'lanish uchun quyidagi raqamlarga murojaat qiling: \n{config.ADMIN_PHONE}")


# ============================================================================
# Оформление заказа книги (FSM)
# ============================================================================
class OrderBook(StatesGroup):
    waiting_for_category = State()
    waiting_for_count = State()  # для обычных заказов
    waiting_for_count_confirm = State()  # для обычных заказов
    # Для комбинированного заказа "Ikkalasidanham"
    waiting_for_count_student = State()  # количество для Student book
    waiting_for_count_workbook = State()  # количество для Workbook
    waiting_for_ikkalasidanham_confirm = State()  # подтверждение комбинированного заказа
    waiting_for_school_input = State()
    waiting_for_school_confirm = State()
    waiting_for_final_confirm = State()


# Заказ для учителей
@router.message(lambda message: message.text == "Kitobga buyurtma berish")
async def teacher_order_book_start(message: types.Message, state: FSMContext):
    await state.set_state(OrderBook.waiting_for_category)
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Student book"), KeyboardButton(text="Workbook")],
            [KeyboardButton(text="Ikkalasidanham")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Iltimos, kitob turini tanlang:", reply_markup=reply_keyboard)


# Заказ для рабочих
@router.message(lambda message: message.text == "Buyurtma berish" and message.from_user.id in config.WORKER_IDS)
async def worker_order_book_start(message: types.Message, state: FSMContext):
    await state.set_state(OrderBook.waiting_for_category)
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Student book"), KeyboardButton(text="Workbook")],
            [KeyboardButton(text="Ikkalasidanham")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer("Iltimos, kitob turini tanlang:", reply_markup=reply_keyboard)


@router.message(OrderBook.waiting_for_category)
async def order_book_category_chosen(message: types.Message, state: FSMContext):
    order_category = message.text
    if order_category not in ["Student book", "Workbook", "Ikkalasidanham"]:
        await message.answer("Noto'g'ri tanlov, iltimos, qaytadan tanlang.")
        return
    if order_category in ["Student book", "Workbook"]:
        await state.update_data(order_category=order_category, count=1)
        await state.set_state(OrderBook.waiting_for_count)
        if order_category == "Student book":
            inline_kb = keyboards.order_count_keyboard()
            photo = FSInputFile("images/Students_book.png")
            await message.answer_photo(photo=photo, caption="Kitobning sonini belgilang. Hozirgi son: 1",
                                       reply_markup=inline_kb)
        else:
            inline_kb = keyboards.order_count_keyboard()
            photo = FSInputFile("images/Workbook.png")
            await message.answer_photo(photo=photo, caption="Kitobning sonini belgilang. Hozirgi son: 1",
                                       reply_markup=inline_kb)
    else:
        # Комбинированный заказ "Ikkalasidanham"
        await state.update_data(order_category="Ikkalasidanham", student_count=1, workbook_count=0)
        await state.set_state(OrderBook.waiting_for_count_student)
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="-", callback_data="order:ikkalasidanham_student:decrease"),
             types.InlineKeyboardButton(text="+", callback_data="order:ikkalasidanham_student:increase")],
            [types.InlineKeyboardButton(text="Buyurtma berish", callback_data="order:ikkalasidanham_student:submit")]
        ])
        photo = FSInputFile("images/Students_book.png")
        await message.answer_photo(photo=photo, caption="Student Book (Ikkalasidanham): 1", reply_markup=inline_kb)


@router.callback_query(lambda c: c.data and c.data.startswith("order:count:"))
async def order_count_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    state_data = await state.get_data()
    count = state_data.get("count", 1)
    if data == "order:count:decrease":
        if count > 1:
            count -= 1
        await state.update_data(count=count)
        inline_kb = keyboards.order_count_keyboard()
        await callback_query.message.edit_caption(
            caption=f"Kitobning sonini belgilang. Hozirgi son: {count}",
            reply_markup=inline_kb
        )
        await callback_query.answer()
    elif data == "order:count:increase":
        count += 1
        await state.update_data(count=count)
        inline_kb = keyboards.order_count_keyboard()
        await callback_query.message.edit_caption(
            caption=f"Kitobning sonini belgilang. Hozirgi son: {count}",
            reply_markup=inline_kb
        )
        await callback_query.answer()
    elif data == "order:count:submit":
        await state.set_state(OrderBook.waiting_for_count_confirm)
        count = state_data.get("count", 1)
        confirm_kb = keyboards.order_confirm_keyboard()
        await callback_query.message.answer(
            f"Siz bizning {state_data.get('order_category', 'kitob')} imizdan {count} dona buyurtma bermoqchimisiz?",
            reply_markup=confirm_kb
        )
        await callback_query.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("order:count_confirm:"))
async def order_count_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == "order:count_confirm:yes":
        user_id = callback_query.from_user.id
        user_info = await database.get_user(user_id)
        school = None
        if user_info:
            school = user_info[3]
        if school:
            await state.set_state(OrderBook.waiting_for_school_confirm)
            school_confirm_kb = keyboards.school_confirm_keyboard()
            await callback_query.message.answer(
                f"Sizning ro'yxatdan o'tgan maktab: {school}. Shu maktabga buyurtmani jo'natish kerakmi?",
                reply_markup=school_confirm_kb
            )
        else:
            await state.set_state(OrderBook.waiting_for_school_input)
            await callback_query.message.answer(
                "Yaxshi, unday bo'lsa buyurtma bermoqchi bo'lgan maktabingizni kiriting!")
        await callback_query.answer()
    elif data == "order:count_confirm:no":
        await callback_query.message.answer("Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        await callback_query.answer()


# --- Обработка комбинированного заказа: Student book часть ---
@router.callback_query(lambda c: c.data and c.data.startswith("order:ikkalasidanham_student:"))
async def order_ikkalasidanham_student_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    prefix = "order:ikkalasidanham_student:"
    state_data = await state.get_data()
    student_count = state_data.get("student_count", 1)
    if data == f"{prefix}decrease":
        if student_count > 1:
            student_count -= 1
        await state.update_data(student_count=student_count)
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="-", callback_data=f"{prefix}decrease"),
             types.InlineKeyboardButton(text="+", callback_data=f"{prefix}increase")],
            [types.InlineKeyboardButton(text="Buyurtma berish", callback_data=f"{prefix}submit")]
        ])
        await callback_query.message.edit_caption(
            caption=f"Student Book (Ikkalasidanham): {student_count}",
            reply_markup=inline_kb
        )
        await callback_query.answer()
    elif data == f"{prefix}increase":
        student_count += 1
        await state.update_data(student_count=student_count)
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="-", callback_data=f"{prefix}decrease"),
             types.InlineKeyboardButton(text="+", callback_data=f"{prefix}increase")],
            [types.InlineKeyboardButton(text="Buyurtma berish", callback_data=f"{prefix}submit")]
        ])
        await callback_query.message.edit_caption(
            caption=f"Student Book (Ikkalasidanham): {student_count}",
            reply_markup=inline_kb
        )
        await callback_query.answer()
    elif data == f"{prefix}submit":
        # Удаляем сообщение с информацией о Student Book
        await callback_query.message.delete()
        # Переходим к ветке для Workbook
        await state.set_state(OrderBook.waiting_for_count_workbook)
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="-", callback_data="order:ikkalasidanham_workbook:decrease"),
             types.InlineKeyboardButton(text="+", callback_data="order:ikkalasidanham_workbook:increase")],
            [types.InlineKeyboardButton(text="Buyurtma berish", callback_data="order:ikkalasidanham_workbook:submit")]
        ])
        photo = FSInputFile("images/Workbook.png")
        await callback_query.message.answer_photo(
            photo=photo,
            caption="Workbook (Ikkalasidanham): 0",
            reply_markup=inline_kb
        )
        await callback_query.answer()


# --- Обработка комбинированного заказа: Workbook часть ---
@router.callback_query(lambda c: c.data and c.data.startswith("order:ikkalasidanham_workbook:"))
async def order_ikkalasidanham_workbook_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    prefix = "order:ikkalasidanham_workbook:"
    state_data = await state.get_data()
    workbook_count = state_data.get("workbook_count", 0)
    if data == f"{prefix}decrease":
        if workbook_count > 0:
            workbook_count -= 1
        await state.update_data(workbook_count=workbook_count)
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="-", callback_data=f"{prefix}decrease"),
             types.InlineKeyboardButton(text="+", callback_data=f"{prefix}increase")],
            [types.InlineKeyboardButton(text="Buyurtma berish", callback_data=f"{prefix}submit")]
        ])
        await callback_query.message.edit_caption(
            caption=f"Workbook (Ikkalasidanham): {workbook_count}",
            reply_markup=inline_kb
        )
        await callback_query.answer()
    elif data == f"{prefix}increase":
        workbook_count += 1
        await state.update_data(workbook_count=workbook_count)
        inline_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="-", callback_data=f"{prefix}decrease"),
             types.InlineKeyboardButton(text="+", callback_data=f"{prefix}increase")],
            [types.InlineKeyboardButton(text="Buyurtma berish", callback_data=f"{prefix}submit")]
        ])
        await callback_query.message.edit_caption(
            caption=f"Workbook (Ikkalasidanham): {workbook_count}",
            reply_markup=inline_kb
        )
        await callback_query.answer()
    elif data == f"{prefix}submit":
        # Удаляем сообщение с информацией о Workbook
        await callback_query.message.delete()
        # Переходим к финальному подтверждению комбинированного заказа
        await state.set_state(OrderBook.waiting_for_ikkalasidanham_confirm)
        state_data = await state.get_data()
        student_count = state_data.get("student_count", 1)
        workbook_count = state_data.get("workbook_count", 0)
        combined_text = f"Student book: {student_count}, Workbook: {workbook_count}"
        confirm_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Ha", callback_data="order:ikkalasidanham_confirm:yes"),
             types.InlineKeyboardButton(text="Yo'q", callback_data="order:ikkalasidanham_confirm:no")]
        ])
        await callback_query.message.answer(
            f"Siz quyidagi buyurtma bermoqchimisiz?\n{combined_text}",
            reply_markup=confirm_kb
        )
        await callback_query.answer()


# --- Обработка подтверждения комбинированного заказа ---
@router.callback_query(lambda c: c.data and c.data.startswith("order:ikkalasidanham_confirm:"))
async def order_ikkalasidanham_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    # Удаляем сообщение с inline-клавиатурой подтверждения
    await callback_query.message.delete()
    if data == "order:ikkalasidanham_confirm:yes":
        user_id = callback_query.from_user.id
        user_info = await database.get_user(user_id)
        school = user_info[3] if user_info else None
        if school:
            await state.set_state(OrderBook.waiting_for_school_confirm)
            school_confirm_kb = keyboards.school_confirm_keyboard()
            await callback_query.message.answer(
                f"Sizning ro'yxatdan o'tgan maktabingiz: {school}. Shu maktabga buyurtmani jo'natish kerakmi?",
                reply_markup=school_confirm_kb
            )
        else:
            await state.set_state(OrderBook.waiting_for_school_input)
            await callback_query.message.answer(
                "Yaxshi, unday bo'lsa, buyurtma bermoqchi bo'lgan maktabingizni kiriting!")
        await callback_query.answer()
    elif data == "order:ikkalasidanham_confirm:no":
        await callback_query.message.answer("Buyurtma bekor qilindi.", reply_markup=keyboards.teacher_menu_keyboard())
        await state.clear()
        await callback_query.answer()


# Общая часть для SCHOOL и FINAL CONFIRM (для всех заказов)
@router.message(OrderBook.waiting_for_school_input)
async def order_school_input(message: types.Message, state: FSMContext):
    school = message.text
    user_id = message.from_user.id
    await database.update_user(user_id, school=school)
    await state.update_data(school=school)
    await state.set_state(OrderBook.waiting_for_final_confirm)
    final_kb = keyboards.final_confirm_keyboard()
    await message.answer("Buyurtmani tasdiqlaysizmi?", reply_markup=final_kb)


@router.callback_query(lambda c: c.data and c.data.startswith("order:school_confirm:"))
async def order_school_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    if data == "order:school_confirm:yes":
        await state.set_state(OrderBook.waiting_for_final_confirm)
        final_kb = keyboards.final_confirm_keyboard()
        await callback_query.message.answer("Buyurtmani tasdiqlaysizmi?", reply_markup=final_kb)
        await callback_query.answer()
    elif data == "order:school_confirm:no":
        await state.set_state(OrderBook.waiting_for_school_input)
        await callback_query.message.answer("Yaxshi, unday bo'lsa, buyurtma bermoqchi bo'lgan maktabingizni kiriting!")
        await callback_query.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("order:final_confirm:"))
async def order_final_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data
    user_id = callback_query.from_user.id
    state_data = await state.get_data()
    order_category = state_data.get("order_category")
    if order_category == "Ikkalasidanham":
        student_count = state_data.get("student_count", 1)
        workbook_count = state_data.get("workbook_count", 0)
        order_text = f"Student book: {student_count}, Workbook: {workbook_count}"
    else:
        count = state_data.get("count", 1)
        order_text = f"{order_category}: {count}"
    school = state_data.get("school")
    if not school:
        user_info = await database.get_user(user_id)
        if user_info:
            school = user_info[3]
    if data == "order:final_confirm:yes":
        await callback_query.message.answer("Sizning buyurtmangiz haqidagi ma'lumot adminga jo'natildi, "
                                            "javobni kuting.",
                                            reply_markup=ReplyKeyboardRemove())
        user_info = await database.get_user(user_id)
        name_field = "Foydalanuvchi" if user_id in config.WORKER_IDS else "O'qtuvchi"
        user_name = user_info[2] if user_info else "Noma'lum"
        user_phone = user_info[1] if user_info else "Noma'lum"
        order_details = (
            f"Buyurtma:\n"
            f"{name_field}: {user_name} {user_phone}\n"
            f"Kitoblar: {order_text}\n"
            f"Maktab: {school}"
        )
        admin_kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Ha", callback_data=f"admin:order:accept:yes:{user_id}"),
                types.InlineKeyboardButton(text="Yo'q", callback_data=f"admin:order:accept:no:{user_id}")
            ]
        ])
        await callback_query.bot.send_message(config.ADMIN_ID, order_details, reply_markup=admin_kb)
        await state.clear()
        await callback_query.answer()
    elif data == "order:final_confirm:no":
        await callback_query.message.answer("Buyurtma bekor qilindi.", reply_markup=keyboards.teacher_menu_keyboard())
        await state.clear()
        await callback_query.answer()


# Обработчик решения администратора
@router.callback_query(lambda c: c.data and c.data.startswith("admin:order:accept:"))
async def admin_order_accept_callback(callback_query: types.CallbackQuery):
    data_parts = callback_query.data.split(":")
    choice = data_parts[3]  # "yes" или "no"
    teacher_id = int(data_parts[4])
    if choice == "no":
        await callback_query.message.answer("Buyurtma bekor qilindi.")
        await callback_query.bot.send_message(teacher_id, "Sizning buyurtmangiz qabul qilinmadi.",
                                              reply_markup=keyboards.teacher_menu_keyboard())
        await callback_query.answer()
    elif choice == "yes":
        await callback_query.message.answer("Kitobning yetkazib berilishi haqida ma'lumot qoldiring:")
        admin_pending_orders[callback_query.from_user.id] = teacher_id
        await callback_query.answer()


# Обработчик ввода информации администратором о доставке
@router.message(lambda message: message.from_user.id == config.ADMIN_ID and message.text)
async def admin_delivery_info(message: types.Message):
    admin_id = message.from_user.id
    if admin_id in admin_pending_orders:
        teacher_id = admin_pending_orders.pop(admin_id)
        delivery_info = message.text
        await message.bot.send_message(teacher_id, f"Buyurtmangiz haqida ma'lumot: \n"
                                                   f"{delivery_info}\n"
                                                   f"Admin bilan bog'lanish uchun quyidagi raqamlarga murojaat "
                                                   f"qilishingiz mumkin:\n {config.ADMIN_PHONE}",
                                       reply_markup=keyboards.teacher_menu_keyboard())
