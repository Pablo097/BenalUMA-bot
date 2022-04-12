import logging
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import is_registered, is_driver, add_trip
from utils.keyboards import weekdays_keyboard, time_picker_keyboard, time_picker_process
from utils.common import *
import re

# 'New trip' conversation points
TRIP_START, TRIP_DATE, TRIP_HOUR = range(3)
# 'See Offers' conversation points
(SO_START, SO_DATE, SO_HOUR, SO_HOUR_SELECT_RANGE_START,
                SO_HOUR_SELECT_RANGE_STOP) = range(10,15)

# Abort/Cancel buttons
ikbs_abort_trip = [[InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]]
ikbs_cancel_SO = [[InlineKeyboardButton("Cancelar", callback_data="SO_CANCEL")]]

logger = logging.getLogger(__name__)

# Auxiliary functions

def process_time_callback(update, context, command):
    # Checks type of command
    if command == 'trip':
        ikbs = ikbs_abort_trip
    elif command == 'SO':
        ikbs = ikbs_cancel_SO

    # Check if update is callback query or new message
    if update.callback_query:
        is_query = True
        query = update.callback_query
    else:
        is_query = False
        command_key = f"{command}_message"

    # Try to obtain time depending on update type
    if is_query:
        query.answer()
        time = time_picker_process(update, context, ikbs)
        if not time:
            return
    else:
        if command_key in context.user_data:
            sent_message = context.user_data.pop(command_key)
            sent_message.edit_reply_markup(None)
        # Obtain time
        try:
            time = obtain_time_from_string(update.message.text)
        except:
            time = None
        if not time:
            text = f"No se ha reconocido una hora válida. Por favor, introduce una "\
                   f"hora en formato HH:MM de 24 horas."
            reply_markup = time_picker_keyboard(ikbs_list=ikbs)
            context.user_data[command_key] = update.message.reply_text(text,
                                                    reply_markup=reply_markup)
            return

    # Check time validity depending on command
    if command == 'trip' and not is_future_datetime(context.user_data[f"{command}_date"], time):
        text = f"¡No puedes crear un nuevo viaje en el pasado!"\
               f"\nPor favor, introduce una hora válida."
        hour, minutes = time.split(':')
        if not is_query:
            minutes = 0
        reply_markup = time_picker_keyboard(hour, minutes, ikbs)
        if is_query:
            query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            context.user_data[command_key] = update.message.reply_text(text=text,
                                                    reply_markup=reply_markup)
        return

    return time

# 'New trip' functions

def new_trip(update, context):
    """Gives options for offering a new trip"""
    if is_driver(update.effective_chat.id):
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
    time = process_time_callback(update, context, 'trip')
    if not time:
        return TRIP_HOUR
    else:
        if 'trip_message' in context.user_data:
            context.user_data.pop('trip_message')
        dir = context.user_data.pop('trip_dir')
        date = context.user_data.pop('trip_date')
        trip_key = add_trip(dir, update.effective_chat.id, date, time)
        text = escape_markdown("Perfecto. ¡Tu viaje se ha publicado!\n\n",2)
        text += get_formatted_trip(dir, date, trip_key, showDriver=False)
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

# 'See Offers' functions

def see_offers(update, context):
    """Asks for requisites of the trips to show"""
    if is_registered(update.effective_chat.id):
        # Check if command was previously called and remove reply markup associated
        if 'SO_message' in context.user_data:
            sent_message = context.user_data.pop('SO_message')
            sent_message.edit_reply_markup(None)

        keyboard = [[InlineKeyboardButton("Hacia la UMA", callback_data="DIR_UMA"),
                     InlineKeyboardButton("Hacia Benalmádena", callback_data="DIR_BEN")]]
        keyboard += ikbs_cancel_SO
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"Indica la dirección de los viajes ofertados que quieres ver:"
        context.user_data['SO_message'] = update.message.reply_text(text,
                                                    reply_markup=reply_markup)
        return SO_START
    else:
        text = f"Antes de poder usar este comando debes registrarte con el comando /registro."
        update.message.reply_text(text)
    return ConversationHandler.END

def SO_select_date(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "DIR_UMA":
        context.user_data['SO_dir'] = 'toUMA'
    elif query.data == "DIR_BEN":
        context.user_data['SO_dir'] = 'toBenalmadena'
    else:
        logger.warning("Error in SO direction argument.")
        text = f"Error en opción recibida. Abortando..."
        query.edit_message_text(text=text, reply_markup=None)
        return ConversationHandler.END

    reply_markup = weekdays_keyboard(ikbs_cancel_SO)
    text = f"De acuerdo. ¿Para qué día quieres ver los viajes ofertados?"
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SO_DATE

def SO_select_hour(update, context):
    query = update.callback_query
    query.answer()

    context.user_data['SO_date'] = query.data
    text = f"Por último, ¿quieres ver todos los viajes ofertados para este día,"\
           f" o prefieres indicar el rango horario en el que estás interesado?"

    keyboard = [[InlineKeyboardButton("Ver todos", callback_data="SO_ALL"),
                 InlineKeyboardButton("Indicar rango horario", callback_data="SO_RANGE")]]
    keyboard += ikbs_cancel_SO
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SO_HOUR

def SO_select_hour_range_start(update, context):
    query = update.callback_query
    query.answer()

    text = f"De acuerdo. Primero indica la hora de comienzo para buscar viajes ofertados:"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_cancel_SO)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SO_HOUR_SELECT_RANGE_START

def SO_select_hour_range_stop(update, context):
    time = process_time_callback(update, context, 'SO')
    if not time:
        return SO_HOUR_SELECT_RANGE_START
    else:
        context.user_data['SO_time_start'] = time
        text = f"Ahora indica hasta qué hora buscar viajes."\
               f"\n(También puedes mandarme un mensaje con la hora directamente)"
        reply_markup = time_picker_keyboard(ikbs_list=ikbs_cancel_SO)
        if update.callback_query:
            update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            context.user_data['SO_message'] = update.message.reply_text(text=text,
                                                    reply_markup=reply_markup)
    return SO_HOUR_SELECT_RANGE_STOP

def SO_visualize(update, context):
    # Check type of callback
    if update.callback_query:
        is_query = True
        query = update.callback_query
    else:
        is_query = False

    time_start = None
    time_stop = None

    # Check whether we expect an stop time
    if 'SO_time_start' in context.user_data:
        time = process_time_callback(update, context, 'SO')
        if not time:
            return SO_HOUR_SELECT_RANGE_STOP
        else:
            # Check if stop time is greater than start one
            if is_greater_isotime(context.user_data['SO_time_start'], time):
                text = f"¡La hora final del rango debe ser mayor a la inicial!"\
                       f"\nPor favor, introduce una hora válida (mayor que"\
                       f" {context.user_data['SO_time_start']})."
                hour, minutes = time.split(':')
                if not is_query:
                    minutes = 0
                reply_markup = time_picker_keyboard(hour, minutes, ikbs_cancel_SO)
                if is_query:
                    query.edit_message_text(text=text, reply_markup=reply_markup)
                else:
                    context.user_data['SO_message'] = update.message.reply_text(text=text,
                                                            reply_markup=reply_markup)
                return SO_HOUR_SELECT_RANGE_STOP
            else:
                time_start = context.user_data.pop('SO_time_start')
                time_stop = time

    if 'SO_message' in context.user_data:
        context.user_data.pop('SO_message')
    dir = context.user_data.pop('SO_dir')
    date = context.user_data.pop('SO_date')

    text = f"Viajes ofertados hacia {'la *UMA*' if dir=='toUMA' else '*Benalmádena*'}"\
           f" el día *{date[8:10]}/{date[5:7]}*"
    if time_start:
        text += f" entre las *{time_start}* y las *{time_stop}*"
    text += f":\n\n"
    text += get_formatted_offered_trips(dir, date, time_start, time_stop)

    if is_query:
        query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    else:
        update.message.reply_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)

    return ConversationHandler.END

def SO_cancel(update, context):
    """Cancels see offers conversation."""
    query = update.callback_query
    query.answer()
    if 'SO_message' in context.user_data:
        context.user_data.pop('SO_message')
    if 'SO_dir' in context.user_data:
        context.user_data.pop('SO_dir')
    if 'SO_date' in context.user_data:
        context.user_data.pop('SO_date')
    if 'SO_time_start' in context.user_data:
        context.user_data.pop('SO_time_start')
    if 'SO_time_stop' in context.user_data:
        context.user_data.pop('SO_time_stop')
    query.edit_message_text(text="Se ha cancelado la visualización de viajes ofertados.")
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
                CallbackQueryHandler(select_more, pattern='^TIME_PICKER_.*'),
                MessageHandler(Filters.text & ~Filters.command, select_more),
            ],
        },
        fallbacks=[CallbackQueryHandler(trip_abort, pattern='^TRIP_ABORT$'),
                   CommandHandler('nuevoviaje', new_trip)],
    )

    # Create conversation handler for 'see offers'
    SO_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('verofertas', see_offers)],
        states={
            SO_START: [
                CallbackQueryHandler(SO_select_date, pattern='^(DIR_UMA|DIR_BEN)$'),
            ],
            SO_DATE: [
                CallbackQueryHandler(SO_select_hour, pattern=regex_iso_date),
            ],
            SO_HOUR: [
                CallbackQueryHandler(SO_select_hour_range_start, pattern='^(SO_RANGE)$'),
                CallbackQueryHandler(SO_visualize, pattern='^(SO_ALL)$'),
            ],
            SO_HOUR_SELECT_RANGE_START: [
                CallbackQueryHandler(SO_select_hour_range_stop, pattern='^TIME_PICKER_.*'),
                MessageHandler(Filters.text & ~Filters.command, SO_select_hour_range_stop),
            ],
            SO_HOUR_SELECT_RANGE_STOP: [
                CallbackQueryHandler(SO_visualize, pattern='^TIME_PICKER_.*'),
                MessageHandler(Filters.text & ~Filters.command, SO_visualize),
            ],
        },
        fallbacks=[CallbackQueryHandler(SO_cancel, pattern='^SO_CANCEL$'),
                   CommandHandler('verofertas', see_offers)],
    )

    dispatcher.add_handler(trip_conv_handler)
    dispatcher.add_handler(SO_conv_handler)
