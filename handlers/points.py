from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

import database as db
from config import LOW_STOCK_THRESHOLD, VISIT_REMINDER_DAYS

router = Router()


class AddPoint(StatesGroup):
    name = State()
    address = State()
    sell_price = State()
    commission_type = State()
    commission = State()


POINTS_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Все точки"), KeyboardButton(text="➕ Добавить точку")],
        [KeyboardButton(text="🔙 Главное меню")],
    ],
    resize_keyboard=True
)


@router.message(F.text == "🏪 Точки")
async def points_menu(message: Message):
    await message.answer("Раздел точек:", reply_markup=POINTS_MENU)


@router.message(F.text == "📋 Все точки")
async def list_points(message: Message):
    points = await db.get_all_points()
    if not points:
        await message.answer("Точек пока нет. Добавь первую!")
        return

    now = datetime.now()
    text = "🏪 <b>Твои точки:</b>\n\n"
    for p in points:
        stock = await db.get_point_total_stock(p["id"])
        stock_items = await db.get_point_stock(p["id"])

        encashments = await db.get_encashments(point_id=p["id"])
        avg_per_day = 0
        if len(encashments) >= 2:
            total_sold = sum(e["bottles_sold"] for e in encashments[:5])
            days_range = 30
            avg_per_day = total_sold / days_range

        visit_warn = ""
        if p["last_visit"]:
            last = datetime.strptime(p["last_visit"], "%Y-%m-%d %H:%M")
            days_ago = (now - last).days
            if days_ago >= VISIT_REMINDER_DAYS:
                visit_warn = f" ⚠️ Не был {days_ago} дн."

        stock_warn = " 🔴 Мало!" if stock <= LOW_STOCK_THRESHOLD else ""

        text += f"📍 <b>{p['name']}</b>{visit_warn}\n"
        text += f"   Адрес: {p['address'] or '—'}\n"
        text += f"   Цена: {p['sell_price']}₽ | Комиссия: "
        if p["commission_type"] == "percent":
            text += f"{p['commission']}%\n"
        else:
            text += f"{p['commission']}₽\n"
        text += f"   Остаток: {stock} шт.{stock_warn}\n"

        if stock_items:
            for item in stock_items:
                text += f"     • {item['aroma_name']}: {item['quantity']} шт.\n"

        if avg_per_day > 0:
            days_left = int(stock / avg_per_day) if avg_per_day > 0 else 0
            text += f"   📈 Темп: ~{avg_per_day:.1f} шт/день → хватит на ~{days_left} дн.\n"

        last_visit_str = p["last_visit"] or "никогда"
        text += f"   Последний визит: {last_visit_str}\n\n"

    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "➕ Добавить точку")
async def start_add_point(message: Message, state: FSMContext):
    await state.set_state(AddPoint.name)
    await message.answer("Введи название точки (например: Магазин Радуга):", reply_markup=ReplyKeyboardRemove())


@router.message(AddPoint.name)
async def point_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddPoint.address)
    await message.answer("Введи адрес точки (или отправь - чтобы пропустить):")


@router.message(AddPoint.address)
async def point_address(message: Message, state: FSMContext):
    address = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(address=address)
    await state.set_state(AddPoint.sell_price)
    await message.answer("Цена продажи одного флакона на этой точке (₽):")


@router.message(AddPoint.sell_price)
async def point_sell_price(message: Message, state: FSMContext):
    try:
        price = float(message.text.strip().replace(",", "."))
        await state.update_data(sell_price=price)
        await state.set_state(AddPoint.commission_type)
        await message.answer(
            "Как считается комиссия магазина?",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Фиксированная сумма (₽)")],
                    [KeyboardButton(text="Процент от цены (%)")],
                ],
                resize_keyboard=True
            )
        )
    except ValueError:
        await message.answer("Введи число, например: 400")


@router.message(AddPoint.commission_type)
async def point_commission_type(message: Message, state: FSMContext):
    if "фиксирован" in message.text.lower():
        await state.update_data(commission_type="fixed")
        await message.answer("Введи сумму комиссии в рублях (например: 100):", reply_markup=ReplyKeyboardRemove())
    elif "процент" in message.text.lower():
        await state.update_data(commission_type="percent")
        await message.answer("Введи процент комиссии (например: 25):", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Выбери один из вариантов")
        return
    await state.set_state(AddPoint.commission)


@router.message(AddPoint.commission)
async def point_commission(message: Message, state: FSMContext):
    try:
        commission = float(message.text.strip().replace(",", "."))
        data = await state.get_data()
        await db.add_point(
            data["name"], data["address"],
            data["sell_price"], commission, data["commission_type"]
        )
        await state.clear()

        comm_str = f"{commission}%" if data["commission_type"] == "percent" else f"{commission}₽"
        sell = data["sell_price"]
        if data["commission_type"] == "percent":
            comm_val = sell * commission / 100
        else:
            comm_val = commission

        await message.answer(
            f"✅ Точка <b>{data['name']}</b> добавлена!\n\n"
            f"💰 Цена продажи: {sell}₽\n"
            f"🏪 Комиссия магазина: {comm_str} ({comm_val:.0f}₽)\n"
            f"📦 Твоя выручка с флакона (до себестоимости): {sell - comm_val:.0f}₽",
            parse_mode="HTML",
            reply_markup=POINTS_MENU
        )
    except ValueError:
        await message.answer("Введи число")
