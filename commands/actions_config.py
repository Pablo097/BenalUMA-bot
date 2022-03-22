import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from data.database_api import is_registered, is_driver, set_name, set_car, set_slots, set_bizum, set_fee
from utils.keyboards import config_keyboard
from utils.common import *
import re

CONFIG_SELECT, CHANGING_MESSAGE, CHANGING_SLOTS, CHANGING_BIZUM = range(4)

logger = logging.getLogger(__name__)

def config(update, context):
    """Gives options for changing the user configuration"""
    if is_registered(update.effective_chat.id):
        reply_markup = config_keyboard(update.effective_chat.id)

        text = "Aquí puedes modificar la configuración asociada a tu cuenta."
        update.message.reply_text(text, reply_markup=reply_markup)
        return CONFIG_SELECT
    else:
        text = "Antes de poder usar este comando debes registrarte con el comando /registro."
        update.message.reply_text(text)
        return ConversationHandler.END

def config_restart(update, context):
    """Gives options for changing the user configuration"""
    query = update.callback_query
    query.answer()
    reply_markup = config_keyboard(update.effective_chat.id)

    text = "Puedes seguir cambiando ajustes."
    query.edit_message_text(text, reply_markup=reply_markup)
    return CONFIG_SELECT

def change_name(update, context):
    """Lets user change their username"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("Volver", callback_data="CONFIG_BACK")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = ("⚠️ AVISO: Tu nombre y apellidos ayudan a los demás usuarios a reconocerte,"
            " así que deberías intentar no cambiarlos. \nSi aún así quieres cambiarlos"
            " (quizás porque te hubieras equivocado al registrarte), por favor,"
            " mándame de nuevo tu nombre y apellidos.")
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['option'] = 'name'
    context.user_data['sent_message'] = query.message
    return CHANGING_MESSAGE

def config_slots(update, context):
    """Lets driver change their predefined available slots"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("1", callback_data="1"),
            InlineKeyboardButton("2", callback_data="2"),
            InlineKeyboardButton("3", callback_data="3"),
        ],
        [
            InlineKeyboardButton("4", callback_data="4"),
            InlineKeyboardButton("5", callback_data="5"),
            InlineKeyboardButton("6", callback_data="6"),
        ],
        [
            InlineKeyboardButton("Volver", callback_data="CONFIG_BACK"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "¿Cuántos asientos disponibles sueles ofertar?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['option'] = 'slots'
    return CHANGING_SLOTS

def config_bizum(update, context):
    """Lets driver change their Bizum preference"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Sí", callback_data="Yes"),
            InlineKeyboardButton("No", callback_data="No"),
        ],
        [
            InlineKeyboardButton("Volver", callback_data="CONFIG_BACK"),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Indica si aceptas Bizum como forma de pago o no."
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['option'] = 'bizum'
    return CHANGING_BIZUM

def change_car(update, context):
    """Lets driver change their car description"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("Volver", callback_data="CONFIG_BACK")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = ("Escribe la descripción actualizada de tu coche.")
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['option'] = 'car'
    context.user_data['sent_message'] = query.message
    return CHANGING_MESSAGE

def change_fee(update, context):
    """Lets driver change their fee"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("Volver", callback_data="CONFIG_BACK")]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = ("Escribe el precio del trayecto por pasajero (máximo 1,5€).")
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['option'] = 'fee'
    context.user_data['sent_message'] = query.message
    return CHANGING_MESSAGE

def update_user_property(update, context):
    option = context.user_data['option']

    text = ""
    if option == 'name':
        set_name(update.effective_chat.id, update.message.text)
        text = "Nombre de usuario cambiado correctamente."
    elif option == 'car':
        set_car(update.effective_chat.id, update.message.text)
        text = "Descripción del vehículo actualizada correctamente."
    elif option == 'fee':
        try:
            fee = float(re.search("([0-9]*[.,])?[0-9]+", update.message.text).group().replace(',','.'))
        except:
            fee = -1
        if not (fee>=0 and fee<=MAX_FEE):
            text = "Por favor, introduce un número entre 0 y " + str(MAX_FEE).replace('.',',') + "."
            update.message.reply_text(text)
            return CHANGING_MESSAGE
        else:
            set_fee(update.effective_chat.id, fee)
            text = "Precio del trayecto actualizado a " + str(fee).replace('.',',') + "€."

    # Remove possible inline keyboard from previous message
    if 'sent_message' in context.user_data:
        context.user_data['sent_message'].edit_reply_markup(None)
    context.user_data.clear()

    reply_markup = config_keyboard(update.effective_chat.id)
    text += "\nPuedes seguir cambiando ajustes."
    update.message.reply_text(text, reply_markup=reply_markup)
    return CONFIG_SELECT

def update_user_property_callback(update, context):
    query = update.callback_query
    query.answer()

    text = ""
    option = context.user_data['option']
    context.user_data.clear()
    if option == 'slots':
        set_slots(update.effective_chat.id, int(query.data))
        text = "Número de asientos disponibles cambiado correctamente."
    elif option == 'bizum':
        bizum_flag = True if query.data=="Yes" else False
        set_bizum(update.effective_chat.id, bizum_flag)
        text = "Preferencia de Bizum modificada correctamente."

    reply_markup = config_keyboard(update.effective_chat.id)
    text += "\nPuedes seguir cambiando ajustes."
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return CONFIG_SELECT

def config_end(update, context):
    """Ends configuration conversation."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Asistente de configuración de cuenta terminado.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for user configuration
    config_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('config', config)],
        states={
            CONFIG_SELECT: [
                CallbackQueryHandler(change_name, pattern='^CONFIG_NAME$'),
                CallbackQueryHandler(config_slots, pattern='^CONFIG_SLOTS$'),
                CallbackQueryHandler(config_bizum, pattern='^CONFIG_BIZUM$'),
                CallbackQueryHandler(change_car, pattern='^CONFIG_CAR$'),
                CallbackQueryHandler(change_fee, pattern='^CONFIG_FEE$'),
                CallbackQueryHandler(config_end, pattern='^CONFIG_END$'),
            ],
            CHANGING_MESSAGE: [
                MessageHandler(Filters.text & ~Filters.command, update_user_property),
            ],
            CHANGING_SLOTS: [
                CallbackQueryHandler(update_user_property_callback, pattern='^(1|2|3|4|5|6)$')
            ],
            CHANGING_BIZUM: [
                CallbackQueryHandler(update_user_property_callback, pattern='^(Yes|No)$')
            ],
        },
        fallbacks=[CallbackQueryHandler(config_restart, pattern='^CONFIG_BACK$')],
    )

    dispatcher.add_handler(config_conv_handler)
