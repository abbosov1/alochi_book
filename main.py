import asyncio
from aiogram.client.bot import Bot, DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Dispatcher
import logging

from app import config, handlerss, database


async def main():
    storage = MemoryStorage()
    bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

    # Инициализируем базу данных (создаем таблицы, если их нет)
    await database.init_db()

    dp = Dispatcher(storage=storage)
    dp.include_router(handlerss.router)

    # Передаем bot как позиционный аргумент
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
