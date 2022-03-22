import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.database_api import is_driver

def config_keyboard(chat_id):
    keyboard = [
        [
            InlineKeyboardButton("Cambiar nombre de usuario", callback_data="CONFIG_NAME"),
        ]
    ]
    if is_driver(chat_id):
        keyboard += [
            [
                InlineKeyboardButton("Asientos libres", callback_data="CONFIG_SLOTS"),
                InlineKeyboardButton("Aceptar Bizum", callback_data="CONFIG_BIZUM"),
            ], [
                InlineKeyboardButton("Descripción vehículo", callback_data="CONFIG_CAR"),
                InlineKeyboardButton("Establecer precio", callback_data="CONFIG_FEE"),
            ]
        ]
    keyboard += [[InlineKeyboardButton("Terminar", callback_data="CONFIG_END")]]
    return InlineKeyboardMarkup(keyboard)
