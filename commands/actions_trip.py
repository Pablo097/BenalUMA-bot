import logging
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from data.database_api import is_registered, is_driver, add_trip
from utils.keyboards import weekdays_keyboard, time_picker_keyboard, time_picker_process
from utils.common import *
import re

TRIP_START, TRIP_DATE, TRIP_HOUR = range(3)

logger = logging.getLogger(__name__)

def new_trip(update, context):
    """Gives options for offering a new trip"""
    if is_driver(update.effective_chat.id):
        keyboard = [[InlineKeyboardButton("Hacia la UMA", callback_data="DIR_UMA"),
                     InlineKeyboardButton("Hacia Benalmádena", callback_data="DIR_BEN")],
                    [InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"Vas a ofertar un nuevo viaje. Primero, indica en qué dirección viajas:"
        update.message.reply_text(text, reply_markup=reply_markup)
        return TRIP_START
    elif is_registered(update.effective_chat.id):
        text = f"Para poder usar este comando debes tener rol de conductor. "\
               f"Puedes cambiar tu rol a través del comando /config."
    else:
        text = f"Antes de poder usar este comando debes registrarte con el comando /registro."
    update.message.reply_text(text)
    return ConversationHandler.END

def select_date(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "DIR_UMA":
        context.user_data['trip_dir'] = 'toUMA'
    elif query.data == "DIR_BEN":
        context.user_data['trip_dir'] = 'toBenalmadena'
    else:
        logger.warning("Error in trip direction argument.")
        text = f"Error en opción recibida. Abortando..."
        query.edit_message_text(text=text, reply_markup=None)
        return ConversationHandler.END

    reply_markup = weekdays_keyboard()
    text = f"De acuerdo. ¿Para qué día vas a ofertar el viaje?"
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return TRIP_DATE

def select_hour(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['date'] = query.data
    if context.user_data['trip_dir'] == 'toUMA':
        aux_string = 'Benalmádena'
    elif context.user_data['trip_dir'] == 'toBenalmadena':
        aux_string = 'la UMA'
    text = f"Ahora dime, ¿a qué hora pretendes salir desde {aux_string}?"
    reply_markup = time_picker_keyboard(ikbs_list=[[InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]])
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return TRIP_HOUR

def select_more(update, context):
    query = update.callback_query
    query.answer()

    time = time_picker_process(update, context,
                [[InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]])
    if not time:
        return TRIP_HOUR
    else:
        if not is_future_datetime(context.user_data['date'], time):
            text = f"¡No puedes crear un nuevo viaje en el pasado!"\
                   f"\nPor favor, introduce una hora válida."
            hour, minutes = time.split(':')
            reply_markup = time_picker_keyboard(hour, minutes,
                    ikbs_list=[[InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]])
            query.edit_message_text(text=text, reply_markup=reply_markup)
            return TRIP_HOUR
        else:
            add_trip(context.user_data['trip_dir'], update.effective_chat.id,
                    context.user_data['date'], time)
            query.edit_message_text(text="Perfecto. ¡Tu viaje se ha publicado!")

    return ConversationHandler.END

def trip_abort(update, context):
    """Aborts trip conversation."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="La creación de una nueva oferta de viaje se ha abortado.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    regex_iso_date = '^([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])$'

    # Create conversation handler for new trip
    trip_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevoviaje', new_trip)],
        states={
            TRIP_START: [
                CallbackQueryHandler(select_date, pattern='^(DIR_UMA|DIR_BEN)$'),
            ],
            TRIP_DATE: [
                CallbackQueryHandler(select_hour, pattern=regex_iso_date),
            ],
            TRIP_HOUR: [
                # Add option for inputting time manually
                CallbackQueryHandler(select_more, pattern='^TIME_PICKER_.*'),
            ],
        },
        fallbacks=[CallbackQueryHandler(trip_abort, pattern='^TRIP_ABORT$')],
    )

    dispatcher.add_handler(trip_conv_handler)
