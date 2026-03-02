from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db

router = Router()

class MakeSupply(StatesGroup):
choose_point = State()
choose_aroma = State()
quantity = State()
more = State()

@router.message(F.text == “🚚 Поставка”)
async def start_supply(message: Message, state: FSMContext):
points = await db.get_all_points()
if not points:
await message.answer(“Сначала добавь хотя бы одну точку!”)
return

```
kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=p["name"])] for p in points] + [[KeyboardButton(text="🔙 Главное меню")]],
    resize_keyboard=True
)
await state.set_state(MakeSupply.choose_point)
await state.update_data(supplies=[])
await message.answer("На какую точку везёшь товар?", reply_markup=kb)
```

@router.message(MakeSupply.choose_point)
async def supply_choose_point(message: Message, state: FSMContext):
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

await state.update_data(point_id=point["id"], point_name=point["name"])
await ask_aroma(message, state)
```

async def ask_aroma(message: Message, state: FSMContext):
warehouse = await db.get_warehouse()
if not warehouse:
await message.answer(“Склад пуст! Сначала добавь закупку.”)
await state.clear()
return

```
kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=f"{item['aroma_name']} ({item['quantity']} шт.)")] for item in warehouse] +
             [[KeyboardButton(text="✅ Завершить поставку")]],
    resize_keyboard=True
)
await state.set_state(MakeSupply.choose_aroma)
await message.answer("Какой аромат везёшь? (нажми нужный)", reply_markup=kb)
```

@router.message(MakeSupply.choose_aroma)
async def supply_choose_aroma(message: Message, state: FSMContext):
if message.text == “✅ Завершить поставку”:
await finalize_supply(message, state)
return

```
# Извлекаем название аромата (убираем количество в скобках)
aroma_name = message.text.split(" (")[0].strip()
aroma = await db.get_aroma_by_name(aroma_name)
if not aroma:
    await message.answer("Выбери аромат из списка")
    return

warehouse_item = await db.get_warehouse_item(aroma["id"])
if not warehouse_item or warehouse_item["quantity"] <= 0:
    await message.answer("Этого аромата нет на складе")
    return

await state.update_data(current_aroma_id=aroma["id"], current_aroma_name=aroma_name,
                        max_qty=warehouse_item["quantity"])
await state.set_state(MakeSupply.quantity)
await message.answer(
    f"Сколько штук {aroma_name} везёшь?\n(На складе: {warehouse_item['quantity']} шт.)",
    reply_markup=ReplyKeyboardRemove()
)
```

@router.message(MakeSupply.quantity)
async def supply_quantity(message: Message, state: FSMContext):
try:
qty = int(message.text.strip())
data = await state.get_data()

```
    if qty <= 0:
        await message.answer("Введи положительное число")
        return
    if qty > data["max_qty"]:
        await message.answer(f"На складе только {data['max_qty']} шт. Введи меньше.")
        return

    supplies = data.get("supplies", [])
    supplies.append({
        "aroma_id": data["current_aroma_id"],
        "aroma_name": data["current_aroma_name"],
        "quantity": qty
    })
    await state.update_data(supplies=supplies)
    await ask_aroma(message, state)

except ValueError:
    await message.answer("Введи целое число")
```

async def finalize_supply(message: Message, state: FSMContext):
data = await state.get_data()
supplies = data.get(“supplies”, [])

```
if not supplies:
    await message.answer("Ты ничего не добавил в поставку!")
    await state.clear()
    return

point_id = data["point_id"]
total_qty = 0

for s in supplies:
    ok = await db.deduct_from_warehouse(s["aroma_id"], s["quantity"])
    if ok:
        await db.add_to_point_stock(point_id, s["aroma_id"], s["quantity"])
        await db.add_supply(point_id, s["aroma_id"], s["quantity"])
        total_qty += s["quantity"]

await db.update_point_visit(point_id)
await state.clear()

text = f"✅ Поставка на <b>{data['point_name']}</b> оформлена!\n\n"
for s in supplies:
    text += f"• {s['aroma_name']}: {s['quantity']} шт.\n"
text += f"\n📦 Итого привезено: {total_qty} шт."

from handlers.common import MAIN_MENU
await message.answer(text, parse_mode="HTML", reply_markup=MAIN_MENU)
```
