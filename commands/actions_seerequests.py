import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from commands import actions_trip
from data.database_api import is_driver
from messages.format import get_formatted_requests
from utils.keyboards import (weekdays_keyboard, requests_ids_keyboard)
from utils.time_picker import (time_picker_keyboard, process_time_callback)
from utils.common import *
from utils.decorators import registered

# 'See Offers' conversation points
(SR_START, SR_DATE, SR_HOUR, SR_HOUR_SELECT_RANGE_START,
            SR_HOUR_SELECT_RANGE_STOP, SR_VISUALIZE) = range(20,26)
cdh = 'SR'   # Callback Data Header

# Abort/Cancel buttons
ikbs_cancel_SR = [[InlineKeyboardButton("Cancelar", callback_data=ccd(cdh,"CANCEL"))]]

logger = logging.getLogger(__name__)

@registered
def see_requests(update, context):
    """Asks for requisites of the requests to show"""
    # Check if command was previously called and remove reply markup associated
    if 'SR_message' in context.user_data:
        sent_message = context.user_data.pop('SR_message')
        sent_message.edit_reply_markup(None)

    opt = 'DIR'
    keyboard = [[InlineKeyboardButton("Hacia la UMA", callback_data=ccd(cdh,opt,'UMA')),
                 InlineKeyboardButton("Hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))]]
    keyboard += ikbs_cancel_SR
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Indica la dirección de las peticiones de viaje que quieres ver:"
    context.user_data['SR_message'] = update.message.reply_text(text,
                                                reply_markup=reply_markup)
    return SR_START

def SR_select_date(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='DIR'):
        raise SyntaxError('This callback data does not belong to the SR_select_date function.')

    if data[2]  == "UMA":
        context.user_data['SR_dir'] = 'toUMA'
    elif data[2]  == "BEN":
        context.user_data['SR_dir'] = 'toBenalmadena'
    else:
        logger.warning("Error in SR direction argument.")
        text = f"Error en opción recibida. Abortando..."
        query.edit_message_text(text=text, reply_markup=None)
        return ConversationHandler.END

    reply_markup = weekdays_keyboard(cdh, ikbs_cancel_SR)
    text = f"De acuerdo. ¿Para qué día quieres ver las peticiones de viaje?"
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SR_DATE

def SR_select_hour(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the SR_select_hour function.')

    context.user_data['SR_date'] = data[1]
    text = f"Por último, ¿quieres ver todas las peticiones de viaje para este día,"\
           f" o prefieres indicar el rango horario en el que estás interesado?"

    keyboard = [[InlineKeyboardButton("Ver todas", callback_data=ccd(cdh,'ALL')),
                 InlineKeyboardButton("Indicar rango horario", callback_data=ccd(cdh,'RANGE'))]]
    keyboard += ikbs_cancel_SR
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SR_HOUR

def SR_select_hour_range_start(update, context):
    query = update.callback_query
    query.answer()

    text = f"De acuerdo. Primero indica la hora de comienzo para buscar peticiones:"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_cancel_SR)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SR_HOUR_SELECT_RANGE_START

def SR_select_hour_range_stop(update, context):
    time = process_time_callback(update, context, 'SR', ikbs_cancel_SR)
    if not time:
        return SR_HOUR_SELECT_RANGE_START
    else:
        context.user_data['SR_time_start'] = time
        text = f"Ahora indica hasta qué hora buscar peticiones."\
               f"\n(También puedes mandarme un mensaje con la hora directamente)"
        reply_markup = time_picker_keyboard(ikbs_list=ikbs_cancel_SR)
        if update.callback_query:
            update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            context.user_data['SR_message'] = update.message.reply_text(text=text,
                                                    reply_markup=reply_markup)
    return SR_HOUR_SELECT_RANGE_STOP

def SR_visualize(update, context):
    # Check type of callback
    if update.callback_query:
        is_query = True
        query = update.callback_query
    else:
        is_query = False

    time_start = None
    time_stop = None

    # Check whether we expect an stop time
    if 'SR_time_start' in context.user_data:
        time = process_time_callback(update, context, 'SR', ikbs_cancel_SR)
        if not time:
            return SR_HOUR_SELECT_RANGE_STOP
        else:
            # Check if stop time is greater than start one
            if is_greater_isotime(context.user_data['SR_time_start'], time):
                text = f"¡La hora final del rango debe ser mayor a la inicial!"\
                       f"\nPor favor, introduce una hora válida (mayor que"\
                       f" {context.user_data['SR_time_start']})."
                hour, minutes = time.split(':')
                if not is_query:
                    minutes = 0
                reply_markup = time_picker_keyboard(hour, minutes, ikbs_cancel_SR)
                if is_query:
                    query.edit_message_text(text=text, reply_markup=reply_markup)
                else:
                    context.user_data['SR_message'] = update.message.reply_text(text=text,
                                                            reply_markup=reply_markup)
                return SR_HOUR_SELECT_RANGE_STOP
            else:
                time_start = context.user_data.pop('SR_time_start')
                time_stop = time

    if 'SR_message' in context.user_data:
        del context.user_data['SR_message']
    dir = context.user_data['SR_dir']
    date = context.user_data['SR_date']

    text = f"Peticiones de viaje hacia {'la *UMA*' if dir=='toUMA' else '*Benalmádena*'}"\
           f" el día *{date[8:10]}/{date[5:7]}*"
    if time_start:
        text += f" entre las *{time_start}* y las *{time_stop}*"
    text += f":\n\n"
    text_aux, key_list = get_formatted_requests(dir, date, time_start, time_stop)
    if text_aux:
        text += text_aux
    else:
        text += "No existen peticiones de viaje en las fechas seleccionadas\."

    if is_query:
        query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    else:
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)

    if key_list and is_driver(update.effective_chat.id):
        text2 = f"Si quieres ofertar un viaje con las características"\
                f" de alguna de estas peticiones, pulsa el botón correspondiente"\
                f" al número de petición deseada:"
        reply_markup = requests_ids_keyboard(key_list, ikbs_cancel_SR)
        context.user_data['SR_message'] = update.effective_message.reply_text(text2,
                    parse_mode=telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
        return SR_VISUALIZE
    else:
        del context.user_data['SR_dir']
        del context.user_data['SR_date']
        return ConversationHandler.END

def SR_cancel(update, context):
    """Cancels see requests conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('SR_'):
            del context.user_data[key]
    query.edit_message_text(text="Se ha cancelado la visualización de peticiones de viaje.")
    return ConversationHandler.END

def SR_end(update, context):
    """End the conversation when trip requests have already been shown"""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('SR_'):
            del context.user_data[key]
    text = query.message.text
    query.edit_message_text(text[:text.rfind('\n')], entities=query.message.entities)
    return ConversationHandler.END

def add_handlers(dispatcher):
    regex_iso_date = '([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])'

    # Create conversation handler for 'see offers'
    SR_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('verpeticiones', see_requests)],
        states={
            SR_START: [
                CallbackQueryHandler(SR_select_date, pattern=f"^{ccd(cdh,'DIR','(UMA|BEN)')}$"),
            ],
            SR_DATE: [
                CallbackQueryHandler(SR_select_hour, pattern=f"^{ccd(cdh,regex_iso_date)}$"),
            ],
            SR_HOUR: [
                CallbackQueryHandler(SR_select_hour_range_start, pattern=f"^{ccd(cdh,'RANGE')}$"),
                CallbackQueryHandler(SR_visualize, pattern=f"^{ccd(cdh,'ALL')}$"),
            ],
            SR_HOUR_SELECT_RANGE_START: [
                CallbackQueryHandler(SR_select_hour_range_stop, pattern="^TIME_PICKER.*"),
                MessageHandler(Filters.text & ~Filters.command, SR_select_hour_range_stop),
            ],
            SR_HOUR_SELECT_RANGE_STOP: [
                CallbackQueryHandler(SR_visualize, pattern="^TIME_PICKER.*"),
                MessageHandler(Filters.text & ~Filters.command, SR_visualize),
            ],
            SR_VISUALIZE: [
                actions_trip.trip_conv_handler,
                CallbackQueryHandler(SR_end, pattern=f"^{ccd(cdh,'CANCEL')}$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(SR_cancel, pattern=f"^{ccd(cdh,'CANCEL')}$"),
                   CommandHandler('verpeticiones', see_requests)],
    )

    dispatcher.add_handler(SR_conv_handler)
