import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import add_request
from messages.format import (format_request_from_data, get_formatted_request,
                            get_formatted_trips_near_request)
from messages.notifications import notify_new_request
from utils.keyboards import weekdays_keyboard
from utils.time_picker import (time_picker_keyboard, process_time_callback)
from utils.common import *
from utils.decorators import registered, send_typing_action

# 'New request' conversation points
(REQUEST_START, REQUEST_DATE, REQUEST_HOUR, REQUEST_REVIEW) = range(4)
cdh = "REQ"   # Callback Data Header

# Abort/Cancel buttons
ikbs_abort_request = [[InlineKeyboardButton("Abortar", callback_data=ccd(cdh,'ABORT'))]]

logger = logging.getLogger(__name__)

@registered
def new_request(update, context):
    """Gives options for offering a new request"""
    # Check if command was previously called and remove reply markup associated
    if 'request_message' in context.user_data:
        sent_message = context.user_data.pop('request_message')
        sent_message.edit_reply_markup(None)
    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('request_'):
            del context.user_data[key]

    opt = "DIR"
    keyboard = [[InlineKeyboardButton("Hacia la UMA", callback_data=ccd(cdh,opt,'UMA')),
                 InlineKeyboardButton("Hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))]]
    keyboard += ikbs_abort_request
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Vas a publicar una nueva petición de viaje. Recuerda que los viajes"\
           f" ya ofertados se pueden ver y reservar con el comando /verofertas."\
           f"\nPrimero, indica en qué dirección necesitas el viaje:"
    context.user_data['request_message'] = update.message.reply_text(text,
                                                reply_markup=reply_markup)
    return REQUEST_START

def REQ_select_date(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='DIR'):
        raise SyntaxError('This callback data does not belong to the REQ_select_date function.')

    if data[2] == "UMA":
        context.user_data['request_dir'] = 'toUMA'
    elif data[2] == "BEN":
        context.user_data['request_dir'] = 'toBenalmadena'
    else:
        logger.warning("Error in request direction argument.")
        text = f"Error en opción recibida. Abortando..."
        query.edit_message_text(text=text, reply_markup=None)
        return ConversationHandler.END

    reply_markup = weekdays_keyboard(cdh, ikbs_list=ikbs_abort_request)
    text = f"De acuerdo. ¿Para qué día necesitas el viaje?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return REQUEST_DATE

def REQ_select_hour(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the REQ_select_hour function.')

    context.user_data['request_date'] = data[1]
    text = f"Por último, dime a qué hora te gustaría pedir el viaje"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_abort_request)
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return REQUEST_HOUR

@send_typing_action
def reviewing_request(update, context):
    time = process_time_callback(update, context, 'request', ikbs_abort_request)
    if not time:
        return REQUEST_HOUR
    else:
        context.user_data['request_time'] = time
        dir = context.user_data['request_dir']
        date = context.user_data['request_date']

        keyboard = [[InlineKeyboardButton("Publicar petición", callback_data=ccd(cdh,"PUBLISH")),
                    ikbs_abort_request[0][0]]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"Vas a pedir un viaje con los siguientes datos:\n\n"
        text += format_request_from_data(dir, date, time=time)

        # Give an hour up and down of margin to the trips the user might be interested in
        text_aux = get_formatted_trips_near_request(dir, date, time)
        if text_aux:
            text2 = f"\n\n📘 Antes de publicar la petición, que sepas que hay"\
                    f" viajes ofertados cerca de la hora que has indicado que"\
                    f" quizás te interesen:\n\n"
            text += escape_markdown(text2, 2) + text_aux
            text2 = f"\n\nPara reservar viajes ya ofertados, usa el comando"\
                    f" /verofertas. ¿Estás seguro de que quieres publicar tu"\
                    f" petición de viaje de todos modos?"
            text += escape_markdown(text2, 2)
        else:
            text2 = f"\n\n¿Quieres publicarlo? Todos los conductores con las"\
                    f" notificaciones sobre peticiones activadas recibirán un"\
                    f" mensaje sobre tu publicación."
            text += escape_markdown(text2, 2)

        if update.callback_query:
            update.callback_query.edit_message_text(text=text, reply_markup=reply_markup,
                                    parse_mode=telegram.ParseMode.MARKDOWN_V2)
        else:
            context.user_data['request_message'] = update.message.reply_text(text=text,
                    reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return REQUEST_REVIEW

def publish_request(update, context):
    query = update.callback_query
    query.answer()

    dir = context.user_data.pop('request_dir')
    date = context.user_data.pop('request_date')
    time = context.user_data.pop('request_time')
    request_key = add_request(dir, update.effective_chat.id, date, time)

    text = escape_markdown("Perfecto. ¡Tu petición de viaje se ha publicado!\n\n",2)
    text += get_formatted_request(dir, date, request_key)
    text2 = f"\n\nTu petición se eliminará cuando reserves un asiento en un viaje"\
            f" que salga entre una hora antes y una después de la que has pedido"\
            f" (te notificaré si se publica algún viaje con esas características)."\
            f" Siempre puedes eliminar manualmente tu petición con el comando"\
            f" /mispeticiones en caso de que ya no la necesites."
    text += escape_markdown(text2, 2)
    query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)

    notify_new_request(context, dir, update.effective_chat.id, date, time)

    for key in list(context.user_data.keys()):
        if key.startswith('request_'):
            del context.user_data[key]
    return ConversationHandler.END

def request_abort(update, context):
    """Aborts request conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('request_'):
            del context.user_data[key]
    query.edit_message_text(text="La creación de una nueva petición de viaje se ha abortado.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    regex_iso_date = '([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])'

    # Create conversation handler for 'new request'
    request_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevapeticion', new_request)],
        states={
            REQUEST_START: [
                CallbackQueryHandler(REQ_select_date, pattern=f"^{ccd(cdh,'DIR','(UMA|BEN)')}$"),
            ],
            REQUEST_DATE: [
                CallbackQueryHandler(REQ_select_hour, pattern=f"^{ccd(cdh,regex_iso_date)}$"),
            ],
            REQUEST_HOUR: [
                CallbackQueryHandler(reviewing_request, pattern='^TIME_PICKER.*'),
                MessageHandler(Filters.text & ~Filters.command, reviewing_request),
            ],
            REQUEST_REVIEW: [
                CallbackQueryHandler(publish_request, pattern=f"^{ccd(cdh,'PUBLISH')}$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(request_abort, pattern=f"^{ccd(cdh,'ABORT')}$"),
                   CommandHandler('nuevapeticion', new_request)],
    )

    dispatcher.add_handler(request_conv_handler)
