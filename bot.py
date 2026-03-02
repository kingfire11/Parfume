import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database import init_db
from handlers import common, points, warehouse, supply, encashment, expenses, stats, export

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.include_router(common.router)
    dp.include_router(points.router)
    dp.include_router(warehouse.router)
    dp.include_router(supply.router)
    dp.include_router(encashment.router)
    dp.include_router(expenses.router)
    dp.include_router(stats.router)
    dp.include_router(export.router)
    await init_db()
    logger.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
