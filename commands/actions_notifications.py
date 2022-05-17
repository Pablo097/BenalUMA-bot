import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (is_driver, modify_offer_notification,
                                delete_offer_notification,
                                modify_request_notification,
                                delete_request_notification)
from messages.format import (get_markdown2_inline_mention,
                          get_formatted_offers_notif_config,
                          get_formatted_requests_notif_config)
from utils.keyboards import notif_weekday_keyboard, notif_time_keyboard
from utils.common import *
from utils.decorators import registered, send_typing_action

(NOTIF_SELECT_TYPE, NOTIF_OFFERS, NOTIF_OFFERS_CONFIGURE,
            NOTIF_REQUESTS, NOTIF_REQUESTS_CONFIGURE) = range(40,45)
cdh = "NOTIF"   # Callback Data Header

# Abort/Cancel buttons
ikbs_end_notif = [[InlineKeyboardButton("Terminar", callback_data="NOTIF_END")]]
ikbs_back_notif = [[InlineKeyboardButton("↩️ Volver", callback_data="NOTIF_BACK")]]

logger = logging.getLogger(__name__)

def offer_config_text_and_markup(chat_id, is_first=False):
    if is_first:
        text = f"Al no ser conductor, solo puedes configurar las notificaciones"\
                f" acerca de nuevas *ofertas* de viaje:\n\n"
    else:
        text = f"Esta es tu configuración de notificaciones sobre nuevas"\
                f" *ofertas* de viaje:\n\n"

    text2 = get_formatted_offers_notif_config(chat_id)
    if not text2:
        text += f"_No tienes notificaciones configuradas\._"
    else:
        text += f"{text2}"

    text += f"\n\nSi deseas cambiar tus preferencias, indica primero para qué dirección:"

    opt = "OFFERS"
    keyboard = [[InlineKeyboardButton("Viajes hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))],
                [InlineKeyboardButton("Viajes hacia la UMA", callback_data=ccd(cdh,opt,'UMA'))]]
    keyboard += ikbs_end_notif

    return text, InlineKeyboardMarkup(keyboard)

def request_config_text_and_markup(chat_id):
    text = f"Esta es tu configuración de notificaciones sobre nuevas"\
           f" *peticiones* de viaje:\n\n"

    text2 = get_formatted_requests_notif_config(chat_id)
    if not text2:
        text += f"_No tienes notificaciones configuradas\._"
    else:
        text += f"{text2}"

    text += f"\n\nEs recomendable que, siendo conductor, tengas estas "\
            f"notificaciones siempre activadas para todos los días y direcciones, "\
            f"y solo desactives los días que sepas seguro que nunca vas a llevar"\
            f" a nadie\. Si eso es lo que quieres hacer, elige primero la dirección:"

    opt = "REQUESTS"
    keyboard = [[InlineKeyboardButton("Viajes hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))],
                [InlineKeyboardButton("Viajes hacia la UMA", callback_data=ccd(cdh,opt,'UMA'))]]
    keyboard += ikbs_end_notif

    return text, InlineKeyboardMarkup(keyboard)

@send_typing_action
@registered
def notif_config(update, context):
    """Shows and allows changing the notifications configuration"""
    # Check if command was previously called and remove reply markup associated
    if 'notif_message' in context.user_data:
        sent_message = context.user_data.pop('notif_message')
        sent_message.edit_reply_markup(None)

    text = f"Aquí puedes configurar tu configuración de notificaciones\.\n"
    if not is_driver(update.effective_chat.id):
        text2, reply_markup = offer_config_text_and_markup(update.effective_chat.id, True)
        text += text2
        next_state = NOTIF_OFFERS
    else:
        text += f"Elige qué tipo de notificaciones quieres ver:\n"
        opt = "SELECT"
        keyboard = [[InlineKeyboardButton("Nuevas ofertas", callback_data=ccd(cdh,opt,'OFFERS'))],
                    [InlineKeyboardButton("Nuevas peticiones", callback_data=ccd(cdh,opt,'REQUESTS'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        next_state = NOTIF_SELECT_TYPE

    context.user_data['notif_message'] = update.message.reply_text(text,
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return next_state

@send_typing_action
def offers_config(update, context):
    """Shows and allows changing the offers notifications configuration"""
    query = update.callback_query
    query.answer()

    text, reply_markup = offer_config_text_and_markup(update.effective_chat.id)

    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return NOTIF_OFFERS

def requests_config(update, context):
    """Shows and allows changing the requests notifications configuration"""
    query = update.callback_query
    query.answer()

    text, reply_markup = request_config_text_and_markup(update.effective_chat.id)

    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return NOTIF_REQUESTS

def notif_config_dir(update, context):
    """Obtains the direction and offers weekday selections for notifications configuration"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]==cdh and (data[1]=="OFFERS" or data[1]=='REQUESTS'):
        if data[2]=='BEN':
            context.user_data['notif_dir'] = 'toBenalmadena'
        elif data[2]=='UMA':
            context.user_data['notif_dir'] = 'toUMA'
    else:
        raise SyntaxError('This callback data does not belong to the notif_config_dir function.')

    text = f"Indica para qué *día de la semana* quieres configurar las"\
           f" notificaciones sobre {'ofertas' if data[1]=='OFFERS' else 'peticiones'}:"
    opt = ccd(data[1], 'WD')
    reply_markup = notif_weekday_keyboard(cdh, opt, ikbs_back_notif)

    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    if data[1]=='OFFERS':
        return NOTIF_OFFERS_CONFIGURE
    elif data[1]=='REQUESTS':
        return NOTIF_REQUESTS_CONFIGURE

def notif_config_weekday(update, context):
    """Obtains the weekday and offers time selections for notifications configuration"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]==cdh and (data[1]=="OFFERS" or data[1]=='REQUESTS') and data[2]=='WD':
        context.user_data['notif_weekday'] = data[3]
    else:
        raise SyntaxError('This callback data does not belong to the notif_config_time function.')

    text = f"Indica ahora las horas de salida de los viajes sobre los que te"\
           f" interesa ser notificado:"
    opt = ccd(data[1], 'TIME')
    keyboard = [[InlineKeyboardButton("Todo el día", callback_data=ccd(cdh,opt,'ALL')),
                 InlineKeyboardButton("🛑 No notificar", callback_data=ccd(cdh,opt,'CANCEL'))]]
    if data[1]=="OFFERS":
        keyboard.append([InlineKeyboardButton("Elegir rango horario", callback_data=ccd(cdh,opt,'CHOOSE')),
                          ikbs_back_notif[0][0]])
    elif data[1]=="REQUESTS":
        keyboard += ikbs_back_notif

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

def notif_config_time(update, context):
    """Allows choosing a time range for notifications configuration"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and (data[1]=="OFFERS" or data[1]=='REQUESTS') and
                data[2]=='TIME' and data[3]=='CHOOSE'):
        raise SyntaxError('This callback data does not belong to the notif_config_time function.')

    text = f"Elige cuál es la *primera hora de salida* para la que te interesa"\
           f" recibir notificaciones sobre los viajes que se publiquen:"
    opt = ccd(data[1], 'TIME', 'START')
    reply_markup = notif_time_keyboard(cdh, opt, last_hour=23, ikbs_list=ikbs_back_notif)
    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

def notif_config_time_end(update, context):
    """Obtains start hour and allows choosing the end hour for notifications configuration"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if (data[0]==cdh and (data[1]=="OFFERS" or data[1]=='REQUESTS') and
                data[2]=='TIME' and data[3]=='START'):
        start_hour = int(data[4])
        context.user_data['notif_time_start'] = start_hour
    else:
        raise SyntaxError('This callback data does not belong to the notif_config_time_end function.')

    text = f"Ahora elige cuál es la *última hora de salida* para la que te interesa"\
           f" recibir notificaciones sobre los viajes que se publiquen:"
    opt = ccd(data[1], 'TIME', 'END')
    reply_markup = notif_time_keyboard(cdh, opt, first_hour=start_hour+1, ikbs_list=ikbs_back_notif)
    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)

@send_typing_action
def notif_apply_offers_config(update, context):
    """Applies offers' notifications configuration and shows complete configuration again"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=="OFFERS" and data[2]=='TIME'):
        raise SyntaxError('This callback data does not belong to the notif_apply_offers_config function.')

    chat_id = update.effective_chat.id
    dir = context.user_data.pop('notif_dir')
    weekdays_en_aux = [wd[:3].upper() for wd in weekdays_en]
    weekday = context.user_data.pop('notif_weekday')
    # Parse weekday to valid option
    if weekday=='ALL':
        weekday = None
    else:
        weekday = weekdays_en[weekdays_en_aux.index(weekday)]
    # Apply modification based on input option
    if data[3] == 'ALL':
        modify_offer_notification(chat_id, dir, weekday)
    elif data[3] == 'CANCEL':
        delete_offer_notification(chat_id, dir, weekday)
    elif data[3] == 'END':
        time_range = [context.user_data.pop('notif_time_start')]
        time_range.append(int(data[4]))
        modify_offer_notification(chat_id, dir, weekday, time_range)

    text = f"✅ Tus preferencias para las notificaciones sobre ofertas de viaje"\
           f" han sido actualizadas\.\n\n"
    text2, reply_markup = offer_config_text_and_markup(chat_id)
    text += text2
    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return NOTIF_OFFERS

@send_typing_action
def notif_apply_requests_config(update, context):
    """Applies requests' notifications configuration and shows complete configuration again"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=="REQUESTS" and data[2]=='TIME'):
        raise SyntaxError('This callback data does not belong to the notif_apply_requests_config function.')

    chat_id = update.effective_chat.id
    dir = context.user_data.pop('notif_dir')
    weekdays_en_aux = [wd[:3].upper() for wd in weekdays_en]
    weekday = context.user_data.pop('notif_weekday')
    # Parse weekday to valid option
    if weekday=='ALL':
        weekday = None
    else:
        weekday = weekdays_en[weekdays_en_aux.index(weekday)]
    # Apply modification based on input option
    if data[3] == 'ALL':
        modify_request_notification(chat_id, dir, weekday)
    elif data[3] == 'CANCEL':
        delete_request_notification(chat_id, dir, weekday)

    text = f"✅ Tus preferencias para las notificaciones sobre peticiones de viaje"\
           f" han sido actualizadas\.\n\n"
    text2, reply_markup = request_config_text_and_markup(chat_id)
    text += text2
    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return NOTIF_REQUESTS

def notif_end(update, context):
    """Ends notifications configuration conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('notif_'):
            del context.user_data[key]
    # TODO: FIX THIS. This deletes the markdown.
    text = query.message.text
    query.edit_message_text(text[:text.rfind('\n')], entities=query.message.entities)
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for notifications
    notifications_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('notificaciones', notif_config)],
        states={
            NOTIF_SELECT_TYPE: [
                CallbackQueryHandler(requests_config, pattern=f"^{ccd(cdh,'SELECT','REQUESTS')}$"),
                CallbackQueryHandler(offers_config, pattern=f"^{ccd(cdh,'SELECT','OFFERS')}$")
            ],
            NOTIF_OFFERS: [
                CallbackQueryHandler(notif_config_dir, pattern=f"^{ccd(cdh,'OFFERS','(BEN|UMA)')}$"),
            ],
            NOTIF_OFFERS_CONFIGURE: [
                CallbackQueryHandler(notif_config_weekday, pattern=f"^{ccd(cdh,'OFFERS','WD','.*')}"),
                CallbackQueryHandler(notif_apply_offers_config, pattern=f"^{ccd(cdh,'OFFERS','TIME','(ALL|CANCEL)')}$"),
                CallbackQueryHandler(notif_config_time, pattern=f"^{ccd(cdh,'OFFERS','TIME','CHOOSE')}$"),
                CallbackQueryHandler(notif_config_time_end, pattern=f"^{ccd(cdh,'OFFERS','TIME','START','.*')}"),
                CallbackQueryHandler(notif_apply_offers_config, pattern=f"^{ccd(cdh,'OFFERS','TIME','END','.*')}"),
                CallbackQueryHandler(offers_config, pattern=f"^NOTIF_BACK$"),
            ],
            NOTIF_REQUESTS: [
                CallbackQueryHandler(notif_config_dir, pattern=f"^{ccd(cdh,'REQUESTS','(BEN|UMA)')}$"),
            ],
            NOTIF_REQUESTS_CONFIGURE: [
                CallbackQueryHandler(notif_config_weekday, pattern=f"^{ccd(cdh,'REQUESTS','WD','.*')}"),
                CallbackQueryHandler(notif_apply_requests_config, pattern=f"^{ccd(cdh,'REQUESTS','TIME','(ALL|CANCEL)')}$"),
                CallbackQueryHandler(requests_config, pattern=f"^NOTIF_BACK$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(notif_end, pattern='^NOTIF_END$'),
                   CommandHandler('notificaciones', notif_config)],
    )

    dispatcher.add_handler(notifications_conv_handler)
