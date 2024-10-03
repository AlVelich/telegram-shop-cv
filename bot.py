import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import register_handlers
from db_worker import UserDatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    db = UserDatabaseManager("pgsql", "test", "test")
    await db.connect()

    register_handlers(dp, db, bot)

    await dp.start_polling()

    await db.disconnect()


if __name__ == '__main__':
    asyncio.run(main())
