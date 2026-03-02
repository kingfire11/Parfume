from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

import database as db

router = Router()

EXPENSE_CATEGORIES = [“🚗 Бензин”, “🏪 Аренда”, “📦 Упаковка”, “📱 Связь”, “🔧 Прочее”]

class AddExpense(StatesGroup):
category = State()
amount = State()
note = State()

@router.message(F.text == “💸 Расходы”)
async def expenses_menu(message: Message, state: FSMContext):
kb = ReplyKeyboardMarkup(
keyboard=[[KeyboardButton(text=c)] for c in EXPENSE_CATEGORIES] + [[KeyboardButton(text=“🔙 Главное меню”)]],
resize_keyboard=True
)
await state.set_state(AddExpense.category)
await message.answer(“Выбери категорию расхода:”, reply_markup=kb)

@router.message(AddExpense.category)
async def expense_category(message: Message, state: FSMContext):
if message.text == “🔙 Главное меню”:
await state.clear()
from handlers.common import MAIN_MENU
await message.answer(“Главное меню:”, reply_markup=MAIN_MENU)
return

```
category = message.text.strip()
await state.update_data(category=category)
await state.set_state(AddExpense.amount)
await message.answer(f"Сумма расхода ({category}), ₽:", reply_markup=ReplyKeyboardRemove())
```

@router.message(AddExpense.amount)
async def expense_amount(message: Message, state: FSMContext):
try:
amount = float(message.text.strip().replace(”,”, “.”))
await state.update_data(amount=amount)
await state.set_state(AddExpense.note)
kb = ReplyKeyboardMarkup(
keyboard=[[KeyboardButton(text=“Пропустить”)]],
resize_keyboard=True
)
await message.answer(“Примечание (или нажми Пропустить):”, reply_markup=kb)
except ValueError:
await message.answer(“Введи сумму числом”)

@router.message(AddExpense.note)
async def expense_note(message: Message, state: FSMContext):
note = None if message.text == “Пропустить” else message.text.strip()
data = await state.get_data()
await db.add_expense(data[“category”], data[“amount”], note)
await state.clear()

```
from handlers.common import MAIN_MENU
await message.answer(
    f"✅ Расход записан!\n{data['category']}: {data['amount']:.0f}₽",
    reply_markup=MAIN_MENU
)
```
