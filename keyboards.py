from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Купить предмет")],
        [KeyboardButton(text="Посмотреть цену предмета")],
        [KeyboardButton(text="Профиль")]
    ],
    resize_keyboard=True, one_time_keyboard=False
)

ask_game_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="CS GO"), KeyboardButton(text="Dota 2"), KeyboardButton(text="Rust")],
        [KeyboardButton(text="Назад"), KeyboardButton(text="Меню")]
    ],
    resize_keyboard=True, one_time_keyboard=False
)

def_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад"), KeyboardButton(text="Меню")]
    ],
    resize_keyboard=True, one_time_keyboard=False
)

profile_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Пополнить баланс")],
         [KeyboardButton(text="Изменить trade link")],
         [KeyboardButton(text="Посмотреть историю")],
         [KeyboardButton(text="Меню")]],
    resize_keyboard=True, one_time_keyboard=False
)

change_tradelink_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отмена")],
         [KeyboardButton(text="Меню")]],
    resize_keyboard=True, one_time_keyboard=False
)

change_mode_kb_on = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад"), KeyboardButton(text="Меню")],
        [KeyboardButton(text="Вкл. Режим покупки")]
    ],
    resize_keyboard=True, one_time_keyboard=False
)

change_mode_kb_off = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Назад"), KeyboardButton(text="Меню")],
        [KeyboardButton(text="Выкл. Режим покупки")]
    ],
    resize_keyboard=True, one_time_keyboard=False
)
