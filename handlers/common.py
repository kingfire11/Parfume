from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

router = Router()

MAIN_MENU = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text=“🏪 Точки”), KeyboardButton(text=“📦 Склад”)],
[KeyboardButton(text=“🚚 Поставка”), KeyboardButton(text=“💰 Инкассация”)],
[KeyboardButton(text=“💸 Расходы”), KeyboardButton(text=“📊 Статистика”)],
[KeyboardButton(text=“📤 Экспорт в Excel”)],
],
resize_keyboard=True
)

@router.message(CommandStart())
async def cmd_start(message: Message):
await message.answer(
“👋 Привет! Я помогаю учитывать продажи масляных духов.\n\n”
“Выбери нужный раздел:”,
reply_markup=MAIN_MENU
)

@router.message(F.text == “🔙 Главное меню”)
async def main_menu(message: Message):
await message.answer(“Главное меню:”, reply_markup=MAIN_MENU)
