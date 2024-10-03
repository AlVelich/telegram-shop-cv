from aiogram import Dispatcher
from aiogram.types import Message
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text
from functools import partial
from keyboards import main_menu_kb
from states import Form
from db_worker import UserDatabaseManager


async def cmd_start(message: Message, state: FSMContext, db: UserDatabaseManager, bot):
    user_data = {
        'user_id': message.from_user.id,
        'username': message.from_user.username,
        'first_name': message.from_user.first_name,
        'last_name': message.from_user.last_name,
        'trade_link': ''
    }
    await db.create_user_account(user_data)
    trade_link = await db.get_user_trade_link(message.from_user.id)
    await state.update_data(price_check=False)
    if not trade_link:
        await Form.get_tradelink.set()
        await message.answer("Пожалуйста, введите trade ссылку для дальнейшей работы с ботом:")
    else:
        await Form.main_menu.set()
        await message.answer("Добро пожаловать в главное меню:", reply_markup=main_menu_kb)


async def cmd_cancel(message: Message, state: FSMContext, db: UserDatabaseManager, bot):
    await state.finish()
    await db.remove_user_from_process(message.from_user.id)
    await Form.main_menu.set()
    await message.answer('Отменено.', reply_markup=main_menu_kb)


async def cmd_menu(message: Message, state: FSMContext, db: UserDatabaseManager, bot):
    await state.finish()
    await db.remove_user_from_process(message.from_user.id)
    await Form.main_menu.set()
    await message.answer('Добро пожаловать в главное меню:', reply_markup=main_menu_kb)


async def cmd_coupon(message: Message, state: FSMContext, db: UserDatabaseManager, bot):
    await state.finish()
    await db.remove_user_from_process(message.from_user.id)
    await Form.main_menu.set()
    await message.answer('Отменено.', reply_markup=main_menu_kb)


def register(dp: Dispatcher, db: UserDatabaseManager, bot):
    dp.register_message_handler(partial(cmd_start, db=db, bot=bot), Command("start"), state="*")
    dp.register_message_handler(partial(cmd_cancel, db=db, bot=bot), Command("cancel"), state="*")
    dp.register_message_handler(partial(cmd_menu, db=db, bot=bot), Text(equals='меню', ignore_case=True), state="*")
