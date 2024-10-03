import time

from db_worker import UserDatabaseManager
import asyncio
import math
import uuid
from datetime import datetime
import random
import socket
import struct
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN
from aifory import AIFORYClient

test = AIFORYClient("", "", "")


async def main():
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)
    db = UserDatabaseManager("pgsql", "test", "test")
    await db.connect()
    while True:
        invoices_ids = await db.get_all_invoices()
        print(invoices_ids)
        for data_lst in invoices_ids:
            cur_status = await test.status_invoice(data_lst[0])
            if cur_status['statusID'] == 1:
                print(cur_status)
                continue
            elif cur_status['statusID'] == 2:
                print(cur_status)
                await db.add_to_user_balance(data_lst[1], data_lst[2])
                await db.update_invoice_status(2, data_lst[0])
                await bot.send_message(text="Оплата произошла успешно, ваш баланс пополнен!", chat_id=data_lst[3])
            elif cur_status['statusID'] == 3:
                print(cur_status)
                await db.update_invoice_status(3, data_lst[0])
                await bot.send_message(text="С оплатой пошло что-то не так, платёж был отменён", chat_id=data_lst[3])


            time.sleep(1)
        time.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())