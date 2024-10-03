import math

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher import FSMContext
from functools import partial

from middlewares import transaction_states

from keyboards import main_menu_kb
from states import Form
from services.market import make_request, check_status
from db_worker import UserDatabaseManager
import asyncio
import json
from config import GAMES
import re
buy_koef = 1.05
async def handle_price_callback(call: CallbackQuery, state: FSMContext, db: UserDatabaseManager):
    callback_data = json.loads(call.data)
    index = callback_data['i']
    in_process_users = await db.get_all_user_in_process()

    user_data = await state.get_data()

    if call.from_user.id in in_process_users:
        selected_item = user_data['items'][index]
        item_id = selected_item['id']
        price = selected_item['price'] / 100
        price_for_user = math.ceil(price * buy_koef * 100) / 100
        user_order_game = user_data['game']
        item_float = selected_item["extra"].get("float", 0)



        await state.update_data(game=user_order_game, item_id=item_id, price=price, price_for_user=price_for_user)
        await Form.confirm_purchase.set()

        user_balance = await db.get_user_balance(call.from_user.id)
        if user_balance >= price_for_user:
            usr_tradelink = await db.get_user_trade_link(call.from_user.id)
            await call.message.answer(
                f"Предложение\nЦена: {price:.2f}₽\n с вашего баланса снимут: {price_for_user}\nID предмета: {item_id}\nFloat: {item_float}\n"
                f"Пожалуйста, проверьте вашу трейд ссылку\n{usr_tradelink}")
            await call.message.answer("Купить? (да/нет):")
            await call.answer()

        else:
            await call.message.answer(f"На вашем балансе недостаточно денег для совершения этой сделки {user_balance}")

    elif user_data["price_check"]:
        await call.message.answer("Вы в режиме просмотра цены!")
    else:
        await call.message.answer("Вы должны заново из меню выбрать необходимое")


async def process_confirm_purchase(message: Message, state: FSMContext, db: UserDatabaseManager):
    user_data = await state.get_data()
    if message.text.lower() == "да":

        user_balance = await db.get_user_balance(message.from_user.id)
        if user_balance >= user_data["price_for_user"]:

            trade_link = await db.get_user_trade_link(message.from_user.id)
            match = re.search(r'partner=(\d+)&token=([\w-]+)', trade_link)
            partner = match.group(1)
            token = match.group(2)

           # await state.update_data(partner=partner, token=token)

            await db.subtract_from_user_balance(message.from_user.id, user_data['price_for_user'])
            success, data, custom_id = make_request(
                user_data['item_id'],
                user_data['price'],
                GAMES[user_data["game"]][0],
                partner,
                token
            )

            transaction_data = {'user_id': message.from_user.id, 'custom_id': custom_id,
                                'transaction_state': transaction_states[0], 'item_name': user_data["item_name"],
                                'price': user_data["price"], 'trade_link': trade_link, 'status_code': 0}

            await db.transaction_add(transaction_data)

            if success:
                await message.answer(
                    f'Купил {user_data["item_name"]}\nID: {user_data["item_id"]}\нЦена: {user_data["price"]:.2f} руб.\нCustom_id: {custom_id}')
                await state.finish()
                await asyncio.sleep(4)

                last_status = None
                while True:
                    await asyncio.sleep(1)
                    status_success, status_data = check_status(custom_id, GAMES[user_data["game"]][0])
                    if status_success:
                        stage = status_data.get('stage')
                        trade_id = status_data.get('trade_id')
                        bot_id = status_data.get('bot_id')

                        if stage == '1' and (bot_id is None or trade_id is None):
                            status = ('Ожидаем создание обмена, если в течении 15 минут не пришёл трейд, то деньги автоматически вернутся на баланс.'
                                      '\n Следить за статусом можно в профиле')
                            await db.update_transac_status(custom_id, 1, transaction_states[1])
                        elif stage == '1' and trade_id != 0 and not (bot_id is None or trade_id is None):
                            status = 'Обмен создан, ожидаем принятия обмена пользователем'
                            await db.update_transac_status(custom_id, 2, transaction_states[2])
                        elif stage == '2':
                            status = 'Предмет передан'
                            await message.answer(status)
                            await db.update_transac_status(custom_id, 3, transaction_states[3])
                            await Form.main_menu.set()
                            await message.answer("Возврат в меню главное меню:", reply_markup=main_menu_kb)
                            break
                        elif stage == '5':
                            status = 'Обмен отменен, деньги возвращены на баланс'
                            await message.answer(status)
                            await db.update_transac_status(custom_id, 4, transaction_states[4])
                            await db.add_to_user_balance(message.from_user.id, user_data["price_for_user"])
                            await Form.main_menu.set()
                            await message.answer("Возврат в меню главное меню:", reply_markup=main_menu_kb)
                            break
                        else:
                            status = f'Ошибка проверки статуса: {status_data}'
                            await db.update_transac_status(custom_id, 5, transaction_states[5])
                            await message.answer(status)
                            break

                        if status != last_status:
                            await message.answer(status)
                            last_status = status
            else:
                await message.answer(
                    f'Не удалось купить {user_data["item_name"]} (ID: {user_data["item_id"]}) (custom_id: {custom_id})')
                print(data)
                await db.add_to_user_balance(message.from_user.id, user_data["price_for_user"])
                await message.answer(
                    f'Деньги были возвращены на баланс')
                await db.update_transac_status(custom_id, 6, transaction_states[6])
                await state.finish()
                await db.remove_user_from_process(message.from_user.id)
                await Form.main_menu.set()
                await message.answer('Добро пожаловать в главное меню:', reply_markup=main_menu_kb)
        else:
            await message.answer(f"На вашем балансе недостаточно денег для совершения этой сделки {user_balance}")
    else:
        await message.answer("Покупка отменена.")
        await state.finish()
        await db.remove_user_from_process(message.from_user.id)
        await Form.main_menu.set()
        await message.answer('Добро пожаловать в главное меню:', reply_markup=main_menu_kb)


def register(dp: Dispatcher, db: UserDatabaseManager):
    dp.register_callback_query_handler(partial(handle_price_callback, db=db), lambda c: c.data.startswith('{'),
                                       state="*")
    dp.register_message_handler(partial(process_confirm_purchase, db=db), state=Form.confirm_purchase)
