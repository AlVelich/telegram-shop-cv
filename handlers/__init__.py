from aiogram import Dispatcher
from . import commands, messages, callbacks


def register_handlers(dp: Dispatcher, db, bot):
    commands.register(dp, db, bot)
    messages.register(dp, db, bot)
    callbacks.register(dp, db)
