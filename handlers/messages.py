import json
import math
import random
import socket
import struct
import uuid
from datetime import datetime
from io import BytesIO

import aiohttp
from aiogram import Dispatcher, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from functools import partial

from aifory import AIFORYClient
from keyboards import main_menu_kb, ask_game_kb, def_kb, profile_kb, change_tradelink_kb, \
    change_mode_kb_off, change_mode_kb_on
from states import Form
from services.market import get_balance, get_price_list, send_image
from db_worker import UserDatabaseManager
from aiogram import Bot
from config import GAMES
from services.steam import SteamName
import re

buy_koef = 1.05
steam_nick = SteamName()
pay_in_main = AIFORYClient(
    "",
    "",
    "")

states_dict = {3: "🟢", 4: "🔴", 5: "🔴", 6: "🔴"}


def can_convert_to_float(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


async def handle_main_menu(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    current_state = await state.get_state()
    print(f"Current state in handle_main_menu: {current_state}")
    users_in_process = await db.get_all_user_in_process()
    is_admin = await db.user_is_admin(message.from_user.id)

    if current_state != Form.main_menu.state:
        return

    # if not is_admin:
    #     return

    if message.text == "Купить предмет":
        if not (message.from_user.id in users_in_process):
            await state.update_data(price_check=False)
            await message.answer("Выберите игру:", reply_markup=ask_game_kb)
            await Form.ask_game.set()
        else:
            await message.answer(
                "Вы уже в процессе совершения сделки, попробуйте подождать немного, или обратитесь в поддержку")

    elif message.text == "Посмотреть цену предмета":
        await state.update_data(price_check=True)
        await message.answer("Вы выбрали опцию 'Посмотреть цену предмета'")
        await message.answer("Выберите игру:", reply_markup=ask_game_kb)
        await Form.ask_game.set()

    elif message.text == "Профиль":
        await state.finish()
        await Form.profile_st.set()
        profile_light_data_pt1 = await db.get_user_profile_data(message.from_user.id)
        profile_light_data_pt2 = await db.get_profile_user_data(message.from_user.id)

        text = f"""Пользователь: {profile_light_data_pt2['username']}
Количество успешных покупок: {profile_light_data_pt1[0]}
Количество неудачных покупок: {profile_light_data_pt1[1]}
Баланс: {profile_light_data_pt2['balance']}
ID: {message.from_user.id}
Trade link: <a href='{profile_light_data_pt2['trade_link']}'>{profile_light_data_pt2['steam_nickname']}</a>"""
        await message.answer(text, reply_markup=profile_kb, parse_mode=types.ParseMode.HTML)


async def process_trade_link(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    trade_link = message.text
    match = re.search(r'partner=(\d+)&token=([\w-]+)', trade_link)

    if match:
        await db.update_trade_link(message.from_user.id, trade_link,
                                   steam_nick.get_steam_username_from_trade_url(trade_link))
        await state.finish()
        await Form.main_menu.set()
        await message.answer("Трейд ссылка принята.", reply_markup=main_menu_kb)
    else:
        await message.answer("Неверный формат трейд ссылки. Попробуйте еще раз.")


async def ask_game(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    answer = message.text

    user_data = await state.get_data()

    if answer in GAMES:
        await state.update_data(game=answer)
        if user_data.get("price_check", False):
            balance = 1.00
        else:
            balance = 1  # get_balance()
        if balance is not None:
            user_data = await state.get_data()

            if not user_data.get("price_check", False):
                await db.add_user_to_process(message.from_user.id)
            await Form.buy_menu.set()
            await message.answer("Пришлите название предмета:", reply_markup=def_kb)
        else:
            await Form.main_menu.set()
            await message.answer("Не удалось получить баланс аккаунта. Попробуйте позже.", reply_markup=main_menu_kb)
    elif answer in ["Назад"]:
        await Form.main_menu.set()
        await message.answer("Добро пожаловать в главное меню:", reply_markup=main_menu_kb)
    else:
        await message.answer("Неверный формат ответа! Попробуйте снова.")


async def buy_menu(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    item_name = message.text
    await state.update_data(item_name=item_name)
    await Form.buy_menu_confirm.set()
    await message.answer("Выполняю загрузку данных...")
    await process_buy_menu_confirm(message, state, db, bot)


async def send_image_with_text_and_keyboard(url: str, chat_id: int, bot: Bot, text, kb):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                image = InputFile(BytesIO(image_data), filename="image.png")
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image,
                    caption=text,
                    reply_markup=kb
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)


async def process_buy_menu_confirm(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    user_data = await state.get_data()
    item_name = user_data.get("item_name")

    if not item_name.lower() == "назад":

        success, data = get_price_list(item_name, GAMES[user_data["game"]][0])
        if success:
            items = data
            if items:
                sorted_items = sorted(items, key=lambda x: x['price'])[:10]
                builder = InlineKeyboardMarkup(row_width=2)

                for index, item in enumerate(sorted_items):
                    item_id = item['id']
                    price = item['price'] / 100
                    price_for_user = math.ceil(price * buy_koef * 100) / 100
                    button_data = json.dumps({"i": index})
                    print(button_data)
                    button_text = f"Цена: {price:.2f}₽"
                    builder.insert(
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=button_data
                        )
                    )
                print(sorted_items)
                await state.update_data(items=sorted_items)
                await send_image_with_text_and_keyboard(url=f'https://api.steamapis.com/image/item/{GAMES[user_data["game"]][1]}/{user_data["item_name"]}', chat_id=message.chat.id, text="Выберите товар:", kb=builder, bot=bot)

               # await send_image(
                #    f'https://api.steamapis.com/image/item/{GAMES[user_data["game"]][1]}/{user_data["item_name"]}',
                #    message.chat.id, bot)


                #await message.answer("Выберите товар:", reply_markup=builder)

                if user_data["price_check"]:
                    await message.answer("Если хотите вернуться, нажмите кнопку 'Назад'",
                                         reply_markup=change_mode_kb_on)
                else:
                    await message.answer("Если хотите вернуться, нажмите кнопку 'Назад'", reply_markup=def_kb)
            else:
                await message.answer(f'Не найдено предложений')
                await state.finish()
                await db.remove_user_from_process(message.from_user.id)
        else:
            await message.answer(f'Ошибка получения списка цен')
            await state.finish()
            await db.remove_user_from_process(message.from_user.id)
    else:
        await state.finish()
        await message.answer("Выберите игру:", reply_markup=ask_game_kb)
        await Form.ask_game.set()


async def trade_link_confirmation_purchase(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    trade_link = message.text
    match = re.search(r'partner=(\d+)&token=([\w-]+)', trade_link)

    if match:
        await db.update_trade_link(message.from_user.id, trade_link)
        usr_tradelink = await db.get_user_trade_link(message.from_user.id)
        await message.answer("Трейд ссылка принята.")
        await Form.trade_link_confirmation.set()
        await message.answer(f"Пожалуйста, проверьте вашу трейд ссылку: да или нет\n{usr_tradelink}")
    else:
        await message.answer("Неверный формат трейд ссылки. Попробуйте еще раз.")


async def process_item_name(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    item_name = message.text
    if item_name in ["Назад", "Меню"]:
        await Form.main_menu.set()
        await message.answer("Добро пожаловать в главное меню:", reply_markup=main_menu_kb)
        return

    await state.update_data(item_name=item_name)
    await message.answer("Выполняю загрузку данных...")

    user_data = await state.get_data()
    success, data = get_price_list(item_name, GAMES[user_data["game"]][0])
    if success:
        items = data
        if items:
            lowest_price_item = min(items, key=lambda x: x['price'])
            lowest_price_rub = lowest_price_item['price'] / 100
            item_id = lowest_price_item['id']

            price_for_user = math.ceil(lowest_price_rub * buy_koef * 100) / 100

            try:

                await message.answer(
                    f"Лучшее предложение\nЦена: {lowest_price_rub:.2f}₽\n с вашего баланса снимут:{price_for_user}\nID предмета: {item_id}\nКупить? (да/нет):"
                )
                await send_image(
                    f'https://api.steamapis.com/image/item/{GAMES[user_data["game"]][1]}/{user_data["item_name"]}',
                    message.chat.id, bot)
                await Form.confirm_purchase.set()
                await state.update_data(item_id=item_id, price=lowest_price_item['price'],
                                        price_for_user=price_for_user)
            except:
                await message.answer("""Предложений не найдено, возможно, вы ввели название предмета без учета регистра, нужно точное название как в Steam.
Например - <code>Dead Reckoning Chest</code>, а не <code>dead reckoning chest</code>
Например -  <code>AWP | Asiimov (Field-Tested)</code>, а не  <code>AWP | Азимов</code>""")
        else:
            await message.answer(f"""Предложений не найдено, возможно, вы ввели название предмета без учета регистра, нужно точное название как в Steam.
Например - Dead Reckoning Chest, а не dead reckoning chest
Например - AWP | Asiimov (Field-Tested), а не AWP | Азимов""")
            await state.finish()
            await db.remove_user_from_process(message.from_user.id)
    else:
        await message.answer(f'Ошибка получения списка цен')
        await state.finish()
        await db.remove_user_from_process(message.from_user.id)


async def go_back_to_buy_menu(message: Message, state: FSMContext, db: UserDatabaseManager):
    await Form.buy_menu.set()
    await message.answer("Пришлите название предмета:", reply_markup=def_kb)


async def mode_switch(message: Message, state: FSMContext, db: UserDatabaseManager):
    user_data = await state.get_data()

    current_state = await state.get_state()
    print(f"Current state in handle_main_menu: {current_state}")

    if user_data["price_check"]:
        await state.update_data(price_check=False)
        await db.add_user_to_process(message.from_user.id)
        await message.answer("Вы поменяли режим, теперь вы можете покупать внутри проверки цены!",
                             reply_markup=change_mode_kb_off)
    else:
        await state.update_data(price_check=True)
        await db.remove_user_from_process(message.from_user.id)
        await message.answer("Вы поменяли режим, теперь вы не можете покупать внутри проверки цены!",
                             reply_markup=change_mode_kb_on)


async def go_back_to_ask_game(message: Message, state: FSMContext, db: UserDatabaseManager):
    await Form.ask_game.set()
    await message.answer("Выберите игру:", reply_markup=ask_game_kb)
    await db.remove_user_from_process(message.from_user.id)


async def profile(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    current_state = await state.get_state()
    print(f"Current state in handle_main_menu: {current_state}")

    if message.text == "Пополнить баланс":
        await Form.pay_in_stage1.set()
        await message.answer(
            "Чтобы пополнить баланс, напишите на сколько вы хотите пополнить баланс в руб. \nминимальное значение 50 руб.",
            reply_markup=def_kb)

    elif message.text == "Изменить trade link":
        await state.finish()
        await Form.change_tradelink.set()
        await message.answer("Пожалуйста, введите новую trade ссылку:", reply_markup=change_tradelink_kb)
    elif message.text == "Посмотреть историю":
        data = await db.get_user_history(message.from_user.id)
        text = "Последние 20 покупок:\n"

        for row in data:
            dt_object = datetime.fromtimestamp(row['timestamp'])
            time = dt_object.strftime('%d/%m/%Y %H:%M')
            buf_text = f"{time}| {row['item_name']} - {row['price_rub']} руб|id = <code>{row['transaction_id']}</code>| {states_dict.get(row['status_code'], '🟡')}\n\n"
            text += buf_text

        await message.answer(text, parse_mode=types.ParseMode.HTML)


async def change_trade_link(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    trade_link = message.text
    match = re.search(r'partner=(\d+)&token=([\w-]+)', trade_link)

    if match:
        await db.update_trade_link(message.from_user.id, trade_link,
                                   steam_nick.get_steam_username_from_trade_url(trade_url=trade_link))
        await state.finish()
        await Form.profile_st.set()
        await message.answer("Трейд ссылка принята.", reply_markup=profile_kb)
    elif trade_link == "Отмена":
        await state.finish()
        await Form.profile_st.set()
        await message.answer("Профиль", reply_markup=profile_kb)
    else:
        await message.answer("Неверный формат трейд ссылки. Попробуйте еще раз.")


async def balance_deposit(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    current_state = await state.get_state()
    print(f"Current state in handle_main_menu: {current_state}")


async def pay_in_stage1(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    money_amount = message.text
    print(money_amount)

    if money_amount == "Назад":
        await state.finish()
        await Form.profile_st.set()
        await message.answer("Ваш профиль. Вернуться в главное меню можно командой /start", reply_markup=profile_kb)

    elif money_amount == "Меню":
        await state.finish()
        await db.remove_user_from_process(message.from_user.id)
        await Form.main_menu.set()
        await message.answer('Добро пожаловать в главное меню:', reply_markup=main_menu_kb)

    elif can_convert_to_float:
        money_float = float(money_amount)
        if money_float >= 150 and money_float <= 100000:
            await state.update_data(dep_money=money_float)
            await Form.pay_in_stage2.set()
            await message.answer(
                f"Вы точно хотите пополнить баланс на {money_float}\n (да/нет)",
                reply_markup=def_kb)
        else:
            await message.answer("Минимальное пополнение 150 руб. макс 100 000 руб.")
    else:
        await message.answer("неожиданный формат ответа")


async def pay_in_stage2(message: Message, state: FSMContext, db: UserDatabaseManager, bot: Bot):
    answer = message.text
    if answer == "Назад" or answer.lower() == "нет":
        await Form.pay_in_stage1.set()
        await message.answer(
            "Чтобы пополнить баланс, напишите на сколько вы хотите пополнить баланс в руб. \nминимальное значение 150 руб.",
            reply_markup=def_kb)

    elif answer == "Меню":
        await state.finish()
        await db.remove_user_from_process(message.from_user.id)
        await Form.main_menu.set()
        await message.answer('Добро пожаловать в главное меню:', reply_markup=main_menu_kb)

    elif answer.lower() == "да":
        user_data = await state.get_data()
        data = {
            "amount": user_data['dep_money'],
            "invoice_id": uuid.uuid4().hex,
            "ttl": 600,
            "web_hook_url": "",
            "success_url": "https://t.me/dotaProfile_bot",
            "failed_url": "https://t.me/dotaProfile_bot",
            "ip": socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff))),
            "user_id": message.from_user.id,
            "time_register": datetime.now().timestamp(),
            "payment_type_id": 4
        }

        coms_pay_in = 1.07
        amount = round(abs(float(data['amount'])), 2)
        data['amount'] = math.ceil((amount + 1) * coms_pay_in)
        invoice_data = await pay_in_main.create_invoice(**data)

        invoice_data_db = {'user_id': message.from_user.id,
                           'chat_id': message.chat.id,
                           'invoice_id': data['invoice_id'],
                           'invoice_status': 1,
                           'money_amount': user_data['dep_money'] * coms_pay_in,
                           'money_to_user': user_data['dep_money']}
        await db.create_invoice(invoice_data_db)

        button_url = InlineKeyboardButton("Перейти к Оплате", url=invoice_data['paymentURL'])
        inline_kb = InlineKeyboardMarkup().add(button_url)

        await message.answer(f"Нажмите на кнопку 'Перейти к Оплате', и следуйте инструкциям в браузере",
                             reply_markup=inline_kb)

        await state.finish()
        await Form.profile_st.set()
        await message.answer("Возврат в профиль", reply_markup=profile_kb)


def register(dp: Dispatcher, db: UserDatabaseManager, bot: Bot):
    dp.register_message_handler(partial(handle_main_menu, db=db, bot=bot),
                                Text(equals=["Купить предмет", "Посмотреть цену предмета", "Профиль"]),
                                state=Form.main_menu)
    dp.register_message_handler(partial(process_trade_link, db=db, bot=bot), state=Form.get_tradelink)
    dp.register_message_handler(partial(ask_game, db=db, bot=bot), state=Form.ask_game)
    dp.register_message_handler(partial(buy_menu, db=db, bot=bot), state=Form.buy_menu)
    # dp.register_message_handler(partial(buy_menu_confirm, db=db, bot=bot), state=Form.buy_menu_confirm)
    dp.register_message_handler(partial(trade_link_confirmation_purchase, db=db, bot=bot),
                                state=Form.trade_link_confirmation_purchase)
    dp.register_message_handler(partial(process_item_name, db=db, bot=bot), state=Form.item_name)
    dp.register_message_handler(partial(pay_in_stage1, db=db, bot=bot), state=Form.pay_in_stage1)
    dp.register_message_handler(partial(pay_in_stage2, db=db, bot=bot), state=Form.pay_in_stage2)

    dp.register_message_handler(partial(go_back_to_buy_menu, db=db), Text(equals="Назад", ignore_case=True),
                                state=Form.buy_menu_confirm)
    dp.register_message_handler(partial(profile, db=db, bot=bot),
                                state=Form.profile_st)
    dp.register_message_handler(partial(change_trade_link, db=db, bot=bot),
                                state=Form.change_tradelink)

    dp.register_message_handler(partial(mode_switch, db=db), Text(equals="Выкл. Режим покупки", ignore_case=True),
                                state=Form.buy_menu_confirm)

    dp.register_message_handler(partial(mode_switch, db=db), Text(equals="Вкл. Режим покупки", ignore_case=True),
                                state=(Form.buy_menu_confirm, Form.mode_switch))
