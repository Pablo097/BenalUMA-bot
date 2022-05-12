import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (is_driver)
from messages.format import (get_markdown2_inline_mention,
                          get_formatted_trip_for_driver,
                          get_formatted_trip_for_passenger,
                          get_user_week_formatted_bookings)
from messages.message_queue import send_message
from utils.keyboards import trips_keyboard
from utils.common import *
from utils.decorators import registered, send_typing_action

(NOTIF_SELECT_TYPE, NOTIF_OFFERS, NOTIF_REQUESTS) = range(40,43)
cdh = "NOTIF"   # Callback Data Header

# Abort/Cancel buttons
ikbs_end_notif = [[InlineKeyboardButton("Terminar", callback_data="NOTIF_END")]]
ikbs_back_notif = [[InlineKeyboardButton("↩️ Volver", callback_data="NOTIF_BACK")]]

logger = logging.getLogger(__name__)

@send_typing_action
@registered
def notif_config(update, context):
    """Shows and allows changing the notifications configuration"""
    # Check if command was previously called and remove reply markup associated
    if 'notif_message' in context.user_data:
        sent_message = context.user_data.pop('notif_message')
        sent_message.edit_reply_markup(None)

    text = f"Aquí puedes configurar tu configuración de notificaciones.\n\n"
    if not is_driver(update.effective_chat.id):
        text += f"Al no ser conductor, solo puedes configurar las notificaciones"\
                f" acerca de nuevas ofertas de viaje:\n"
        text = escape_markdown(text, 2)
        # TODO: Not yet implemented
        # text += get_formatted_offers_notif_config(update.effective_chat.id)
        opt = "OFFERS"
        keyboard = [[InlineKeyboardButton("Viajes hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))],
                    [InlineKeyboardButton("Viajes hacia la UMA", callback_data=ccd(cdh,opt,'UMA'))]]
        keyboard += ikbs_end_notif
        next_state = NOTIF_OFFERS
    else:
        text += f"Elige qué tipo de notificaciones quieres configurar:\n"
        opt = "SELECT"
        keyboard = [[InlineKeyboardButton("Nuevas ofertas", callback_data=ccd(cdh,opt,'OFFERS'))],
                    [InlineKeyboardButton("Nuevas peticiones", callback_data=ccd(cdh,opt,'REQUESTS'))]]
        next_state = NOTIF_SELECT_TYPE

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.user_data['notif_message'] = update.message.reply_text(text,
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return next_state

@send_typing_action
def notif_config_restart(update, context):
    """Shows and allows changing the notifications configuration"""
    query = update.callback_query
    query.answer()

    text = f"Aquí puedes configurar tu configuración de notificaciones.\n\n"
    if not is_driver(update.effective_chat.id):
        text += f"Al no ser conductor, solo puedes configurar las notificaciones"\
                f" acerca de nuevas ofertas de viaje:\n"
        text = escape_markdown(text, 2)
        # TODO: Not yet implemented
        # text += get_formatted_offers_notif_config(update.effective_chat.id)
        opt = "OFFERS"
        keyboard = [[InlineKeyboardButton("Viajes hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))],
                    [InlineKeyboardButton("Viajes hacia la UMA", callback_data=ccd(cdh,opt,'UMA'))]]
        keyboard += ikbs_end_notif
        next_state = NOTIF_OFFERS
    else:
        text += f"Elige qué tipo de notificaciones quieres configurar:\n"
        opt = "SELECT"
        keyboard = [[InlineKeyboardButton("Nuevas ofertas", callback_data=ccd(cdh,opt,'OFFERS'))],
                    [InlineKeyboardButton("Nuevas peticiones", callback_data=ccd(cdh,opt,'REQUESTS'))]]
        next_state = NOTIF_SELECT_TYPE

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text, telegram.ParseMode.MARKDOWN_V2, reply_markup=reply_markup)
    return next_state

def notif_end(update, context):
    """Ends notifications configuration conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('notif_'):
            del context.user_data[key]
    query.edit_message_reply_markup(None)
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for notifications
    notifications_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('notificaciones', notif_config)],
        states={
            NOTIF_SELECT_TYPE: [
                CallbackQueryHandler(requests_config, pattern=f"^({cdh}_SELECT_REQUESTS)$"),
                CallbackQueryHandler(offers_config, pattern=f"^({cdh}_SELECT_OFFERS)$")
            ],
            NOTIF_OFFERS: [
                CallbackQueryHandler(offers_config_dir, pattern=f"^({cdh}_OFFERS_(BEN|UMA)$"),
            ],
            NOTIF_REQUESTS: [

            ]
        },
        fallbacks=[CallbackQueryHandler(notif_config_restart, pattern='^NOTIF_BACK$'),
                   CallbackQueryHandler(notif_end, pattern='^NOTIF_END$'),
                   CommandHandler('notificaciones', notif_config)],
    )

    dispatcher.add_handler(notifications_conv_handler)
