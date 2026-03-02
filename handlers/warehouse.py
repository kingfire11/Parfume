from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db

router = Router()


class AddPurchase(StatesGroup):
    aroma_name = State()
    quantity = State()
    cost_price = State()


WAREHOUSE_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Остатки склада"), KeyboardButton(text="🛒 Закупить товар")],
        [KeyboardButton(text="🔙 Главное меню")],
    ],
    resize_keyboard=True
)


@router.message(F.text == "📦 Склад")
async def warehouse_menu(message: Message):
    await message.answer("Склад:", reply_markup=WAREHOUSE_MENU)


@router.message(F.text == "📦 Остатки склада")
async def show_warehouse(message: Message):
    items = await db.get_warehouse()
    if not items:
        await message.answer("Склад пуст. Добавь закупку!")
        return

    text = "📦 <b>Остатки на складе:</b>\n\n"
    total = 0
    for item in items:
        text += f"• {item['aroma_name']}: {item['quantity']} шт. (себест. {item['cost_price']:.0f}₽/шт)\n"
        total += item["quantity"]
    text += f"\n<b>Итого: {total} шт.</b>"
    await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🛒 Закупить товар")
async def start_purchase(message: Message, state: FSMContext):
    await state.set_state(AddPurchase.aroma_name)

    aromas = await db.get_all_aromas()
    text = "Введи название аромата:"
    if aromas:
        text += "\n\nСуществующие ароматы:\n"
        text += "\n".join(f"• {a['name']}" for a in aromas)

    await message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(AddPurchase.aroma_name)
async def purchase_aroma(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(aroma_name=name)
    await state.set_state(AddPurchase.quantity)
    await message.answer(f"Сколько штук {name} закупил?")


@router.message(AddPurchase.quantity)
async def purchase_quantity(message: Message, state: FSMContext):
    try:
        qty = int(message.text.strip())
        await state.update_data(quantity=qty)
        await state.set_state(AddPurchase.cost_price)
        await message.answer("Себестоимость одного флакона (₽)?")
    except ValueError:
        await message.answer("Введи целое число")


@router.message(AddPurchase.cost_price)
async def purchase_cost(message: Message, state: FSMContext):
    try:
        cost = float(message.text.strip().replace(",", "."))
        data = await state.get_data()

        aroma_id = await db.add_aroma(data["aroma_name"])
        await db.add_to_warehouse(aroma_id, data["quantity"], cost)

        import aiosqlite
        from datetime import datetime
        async with aiosqlite.connect(db.DB_PATH) as conn:
            await conn.execute(
                "INSERT INTO purchases (aroma_id, quantity, cost_price, date) VALUES (?, ?, ?, ?)",
                (aroma_id, data["quantity"], cost, datetime.now().strftime("%Y-%m-%d %H:%M"))
            )
            await conn.commit()

        await state.clear()
        total_cost = data["quantity"] * cost
        await message.answer(
            f"✅ Закупка добавлена!\n\n"
            f"🌸 Аромат: {data['aroma_name']}\n"
            f"📦 Количество: {data['quantity']} шт.\n"
            f"💵 Себестоимость: {cost}₽/шт\n"
            f"💰 Потрачено: {total_cost:.0f}₽",
            reply_markup=WAREHOUSE_MENU
        )
    except ValueError:
        await message.answer("Введи число")
