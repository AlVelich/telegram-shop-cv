from aiogram.dispatcher.filters.state import State, StatesGroup

class Form(StatesGroup):
    main_menu = State()
    get_tradelink = State()
    change_tradelink = State()
    buy_menu = State()
    trade_link_confirmation = State()
    ask_game = State()
    trade_link_confirmation_purchase = State()
    item_name = State()
    confirm_purchase = State()
    buy_menu_confirm = State()
    profile_st = State()
    mode_switch = State()
    pay_in_stage1 = State()
    pay_in_stage2 = State()
