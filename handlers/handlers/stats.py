from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta

import database as db

router = Router()

STATS_MENU = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text=“📅 За эту неделю”), KeyboardButton(text=“📆 За этот месяц”)],
[KeyboardButton(text=“📊 За всё время”), KeyboardButton(text=“🏆 Сравнение точек”)],
[KeyboardButton(text=“🔙 Главное меню”)],
],
resize_keyboard=True
)

@router.message(F.text == “📊 Статистика”)
async def stats_menu(message: Message):
await message.answer(“Выбери период:”, reply_markup=STATS_MENU)

async def show_stats(message: Message, date_from=None, date_to=None, period_name=””):
stats = await db.get_stats(date_from, date_to)
expenses = await db.get_expenses(date_from, date_to)

```
total_revenue = sum(s["total_revenue"] or 0 for s in stats)
total_profit = sum(s["total_profit"] or 0 for s in stats)
total_bottles = sum(s["total_bottles"] or 0 for s in stats)
total_expenses = sum(e["amount"] for e in expenses)
net_profit = total_profit - total_expenses

text = f"📊 <b>Статистика {period_name}</b>\n\n"

if not stats:
    text += "Данных пока нет."
    await message.answer(text, parse_mode="HTML")
    return

text += f"💵 Выручка: {total_revenue:.0f}₽\n"
text += f"💰 Прибыль (до расходов): {total_profit:.0f}₽\n"
text += f"💸 Расходы: {total_expenses:.0f}₽\n"
text += f"✅ <b>Чистая прибыль: {net_profit:.0f}₽</b>\n"
text += f"📦 Продано флаконов: {total_bottles} шт.\n\n"

text += "📍 <b>По точкам:</b>\n"
for s in stats:
    text += (
        f"\n🏪 {s['name']}\n"
        f"   Выручка: {s['total_revenue'] or 0:.0f}₽ | "
        f"Прибыль: {s['total_profit'] or 0:.0f}₽ | "
        f"Продано: {s['total_bottles'] or 0} шт.\n"
    )

await message.answer(text, parse_mode="HTML")
```

@router.message(F.text == “📅 За эту неделю”)
async def stats_week(message: Message):
date_from = (datetime.now() - timedelta(days=7)).strftime(”%Y-%m-%d”)
await show_stats(message, date_from=date_from, period_name=“за неделю”)

@router.message(F.text == “📆 За этот месяц”)
async def stats_month(message: Message):
now = datetime.now()
date_from = now.replace(day=1).strftime(”%Y-%m-%d”)
await show_stats(message, date_from=date_from, period_name=f”за {now.strftime(’%B %Y’)}”)

@router.message(F.text == “📊 За всё время”)
async def stats_all(message: Message):
await show_stats(message, period_name=“за всё время”)

@router.message(F.text == “🏆 Сравнение точек”)
async def compare_points(message: Message):
stats = await db.get_stats()

```
if not stats:
    await message.answer("Данных пока нет.")
    return

text = "🏆 <b>Рейтинг точек по прибыли:</b>\n\n"
medals = ["🥇", "🥈", "🥉"]

for i, s in enumerate(stats):
    medal = medals[i] if i < 3 else f"{i+1}."
    text += (
        f"{medal} <b>{s['name']}</b>\n"
        f"   💰 Прибыль: {s['total_profit'] or 0:.0f}₽\n"
        f"   💵 Выручка: {s['total_revenue'] or 0:.0f}₽\n"
        f"   📦 Продано: {s['total_bottles'] or 0} шт.\n\n"
    )

await message.answer(text, parse_mode="HTML")
```
