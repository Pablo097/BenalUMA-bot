import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import add_trip
from messages.format import get_formatted_trip_for_driver
from utils.keyboards import weekdays_keyboard
from utils.time_picker import (time_picker_keyboard, process_time_callback)
from utils.common import *
from utils.decorators import registered, driver

# 'New trip' conversation points
TRIP_START, TRIP_DATE, TRIP_HOUR = range(3)

# Abort/Cancel buttons
ikbs_abort_trip = [[InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]]

logger = logging.getLogger(__name__)

@driver
@registered
def new_trip(update, context):
    """Gives options for offering a new trip"""
    # Check if command was previously called and remove reply markup associated
    if 'trip_message' in context.user_data:
        sent_message = context.user_data.pop('trip_message')
        sent_message.edit_reply_markup(None)

    keyboard = [[InlineKeyboardButton("Hacia la UMA", callback_data="DIR_UMA"),
                 InlineKeyboardButton("Hacia Benalmádena", callback_data="DIR_BEN")]]
    keyboard += ikbs_abort_trip
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Vas a ofertar un nuevo viaje. Primero, indica en qué dirección viajas:"
    context.user_data['trip_message'] = update.message.reply_text(text,
                                                reply_markup=reply_markup)
    return TRIP_START

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

    reply_markup = weekdays_keyboard(ikbs_list=ikbs_abort_trip)
    text = f"De acuerdo. ¿Para qué día vas a ofertar el viaje?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return TRIP_DATE

def select_hour(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['trip_date'] = query.data
    text = f"Ahora dime, ¿a qué hora pretendes salir desde "\
           f"{'Benalmádena' if context.user_data['trip_dir']=='toUMA' else 'la UMA'}?"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_abort_trip)
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return TRIP_HOUR

def select_more(update, context):
    time = process_time_callback(update, context, 'trip', ikbs_abort_trip)
    if not time:
        return TRIP_HOUR
    else:
        if 'trip_message' in context.user_data:
            context.user_data.pop('trip_message')
        dir = context.user_data.pop('trip_dir')
        date = context.user_data.pop('trip_date')
        trip_key = add_trip(dir, update.effective_chat.id, date, time)
        text = escape_markdown("Perfecto. ¡Tu viaje se ha publicado!\n\n",2)
        text += get_formatted_trip_for_driver(dir, date, trip_key)
        if update.callback_query:
            update.callback_query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        else:
            update.message.reply_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        # TODO: Notify users (maybe inside database function)

    # TODO: Add more optional settings before ending new trip config.
    return ConversationHandler.END

def trip_abort(update, context):
    """Aborts trip conversation."""
    query = update.callback_query
    query.answer()
    if 'trip_message' in context.user_data:
        context.user_data.pop('trip_message')
    if 'trip_dir' in context.user_data:
        context.user_data.pop('trip_dir')
    if 'trip_date' in context.user_data:
        context.user_data.pop('trip_date')
    query.edit_message_text(text="La creación de una nueva oferta de viaje se ha abortado.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    regex_iso_date = '^([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])$'

    # Create conversation handler for 'new trip'
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
                CallbackQueryHandler(select_more, pattern='^TIME_PICKER.*'),
                MessageHandler(Filters.text & ~Filters.command, select_more),
            ],
        },
        fallbacks=[CallbackQueryHandler(trip_abort, pattern='^TRIP_ABORT$'),
                   CommandHandler('nuevoviaje', new_trip)],
    )

    dispatcher.add_handler(trip_conv_handler)
