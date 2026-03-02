from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db

router = Router()

class MakeEncashment(StatesGroup):
choose_point = State()
amount = State()
bottles_sold = State()
confirm = State()

@router.message(F.text == “💰 Инкассация”)
async def start_encashment(message: Message, state: FSMContext):
points = await db.get_all_points()
if not points:
await message.answer(“Сначала добавь точку!”)
return

```
kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=p["name"])] for p in points] + [[KeyboardButton(text="🔙 Главное меню")]],
    resize_keyboard=True
)
await state.set_state(MakeEncashment.choose_point)
await message.answer("С какой точки забираешь деньги?", reply_markup=kb)
```

@router.message(MakeEncashment.choose_point)
async def encashment_point(message: Message, state: FSMContext):
if message.text == “🔙 Главное меню”:
await state.clear()
from handlers.common import MAIN_MENU
await message.answer(“Главное меню:”, reply_markup=MAIN_MENU)
return

```
points = await db.get_all_points()
point = next((p for p in points if p["name"] == message.text), None)
if not point:
    await message.answer("Выбери точку из списка")
    return

await state.update_data(point_id=point["id"], point_name=point["name"],
                        sell_price=point["sell_price"],
                        commission=point["commission"],
                        commission_type=point["commission_type"])
await state.set_state(MakeEncashment.amount)
await message.answer(f"Сколько денег забираешь с точки <b>{point['name']}</b>? (₽)",
                     parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
```

@router.message(MakeEncashment.amount)
async def encashment_amount(message: Message, state: FSMContext):
try:
amount = float(message.text.strip().replace(”,”, “.”))
await state.update_data(amount=amount)
await state.set_state(MakeEncashment.bottles_sold)
await message.answer(“Сколько флаконов продано с прошлой инкассации?”)
except ValueError:
await message.answer(“Введи сумму числом”)

@router.message(MakeEncashment.bottles_sold)
async def encashment_bottles(message: Message, state: FSMContext):
try:
bottles = int(message.text.strip())
data = await state.get_data()

```
    # Считаем комиссию магазина
    sell_price = data["sell_price"]
    if data["commission_type"] == "percent":
        commission_per_bottle = sell_price * data["commission"] / 100
    else:
        commission_per_bottle = data["commission"]

    # Получаем среднюю себестоимость со склада
    warehouse = await db.get_warehouse()
    if warehouse:
        avg_cost = sum(w["cost_price"] * w["quantity"] for w in warehouse) / sum(w["quantity"] for w in warehouse)
    else:
        avg_cost = 0

    my_profit_per_bottle = sell_price - commission_per_bottle - avg_cost
    total_my_profit = my_profit_per_bottle * bottles
    total_commission = commission_per_bottle * bottles

    await state.update_data(bottles_sold=bottles, my_profit=total_my_profit,
                            commission_per_bottle=commission_per_bottle,
                            avg_cost=avg_cost)

    text = (
        f"📊 <b>Расчёт инкассации:</b>\n\n"
        f"💵 Забираешь: {data['amount']:.0f}₽\n"
        f"📦 Продано флаконов: {bottles} шт.\n\n"
        f"Расчёт на 1 флакон:\n"
        f"  Цена продажи: {sell_price:.0f}₽\n"
        f"  Комиссия магазина: -{commission_per_bottle:.0f}₽\n"
        f"  Себестоимость: -{avg_cost:.0f}₽\n"
        f"  = Прибыль: {my_profit_per_bottle:.0f}₽/шт\n\n"
        f"💰 <b>Твоя чистая прибыль: {total_my_profit:.0f}₽</b>\n"
        f"🏪 Отдал магазину: {total_commission:.0f}₽"
    )

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Подтвердить"), KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    await state.set_state(MakeEncashment.confirm)
    await message.answer(text, parse_mode="HTML", reply_markup=kb)

except ValueError:
    await message.answer("Введи целое число")
```

@router.message(MakeEncashment.confirm)
async def encashment_confirm(message: Message, state: FSMContext):
if message.text == “✅ Подтвердить”:
data = await state.get_data()
await db.add_encashment(
data[“point_id”], data[“amount”],
data[“bottles_sold”], data[“my_profit”]
)
await db.update_point_visit(data[“point_id”])
await state.clear()

```
    from handlers.common import MAIN_MENU
    await message.answer(
        f"✅ Инкассация записана!\n"
        f"Точка: {data['point_name']}\n"
        f"Забрал: {data['amount']:.0f}₽ | Прибыль: {data['my_profit']:.0f}₽",
        reply_markup=MAIN_MENU
    )
else:
    await state.clear()
    from handlers.common import MAIN_MENU
    await message.answer("Отменено", reply_markup=MAIN_MENU)
```
