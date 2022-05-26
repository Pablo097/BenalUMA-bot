import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import delete_request
from messages.format import get_user_week_formatted_requests, get_formatted_request
from utils.keyboards import requests_keyboard
from utils.common import *
from utils.decorators import registered, send_typing_action

(MR_SELECT, MR_CANCEL, MR_REJECT, MR_EXECUTE) = range(60,64)
cdh = 'MR'   # Callback Data Header

# Abort/Cancel buttons
ikbs_end_MR = [[InlineKeyboardButton("Terminar", callback_data=ccd(cdh,"END"))]]
ikbs_back_MR = [[InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK"))]]

logger = logging.getLogger(__name__)

@send_typing_action
@registered
def my_requests(update, context):
    """Shows all the trip requests for the week ahead"""
    # Check if command was previously called and remove reply markup associated
    if 'MR_message' in context.user_data:
        sent_message = context.user_data.pop('MR_message')
        sent_message.edit_reply_markup(None)
    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('MR_'):
            del context.user_data[key]

    formatted_requests, requests_dict = get_user_week_formatted_requests(update.effective_chat.id)
    if requests_dict:
        text = f"Tus peticiones de viaje para los próximos 7 días:\n\n{formatted_requests}"
        context.user_data['MR_dict'] = requests_dict
        keyboard = [[InlineKeyboardButton("Anular petición", callback_data=ccd(cdh,"CANCEL"))]]
        keyboard += ikbs_end_MR
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['MR_message'] = update.message.reply_text(text,
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return MR_SELECT
    else:
        text = "No tienes peticiones de viaje para la próxima semana."
        update.message.reply_text(text)
    return ConversationHandler.END

@send_typing_action
def my_requests_restart(update, context):
    """Shows all the trip requests for the week ahead"""
    query = update.callback_query
    query.answer()

    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('MR_') and key!='MR_message':
            del context.user_data[key]

    formatted_requests, requests_dict = get_user_week_formatted_requests(update.effective_chat.id)
    if requests_dict:
        text = f"Tus peticiones de viaje para los próximos 7 días:\n\n{formatted_requests}"
        context.user_data['MR_dict'] = requests_dict
        keyboard = [[InlineKeyboardButton("Anular petición", callback_data=ccd(cdh,"CANCEL"))]]
        keyboard += ikbs_end_MR
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return MR_SELECT
    else:
        text = "No tienes peticiones de viaje para la próxima semana."
        query.edit_message_text(text)
    return ConversationHandler.END

def choose_request(update, context):
    """Lets user pick the request to edit"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the choose_request function.')

    next_state = ConversationHandler.END
    requests_dict = context.user_data['MR_dict']
    if data[1] == "CANCEL":
        next_state = MR_CANCEL
        text = f"¿Qué petición de viaje quieres cancelar?"
        reply_markup = requests_keyboard(requests_dict, cdh, ikbs_back_MR)

    query.edit_message_text(text, reply_markup=reply_markup)
    return next_state

def cancel_request(update, context):
    """Cancels the given trip request"""
    query = update.callback_query
    query.answer()

    # Parse request identifiers
    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='ID'):
        raise SyntaxError('This callback data does not belong to the cancel_request function.')
    direction = data[2]
    date = data[3]
    req_key = ';'.join(data[4:])   # Just in case the unique ID constains a ';'
    if direction == 'Ben':
        direction = 'toBenalmadena'
    elif direction == 'UMA':
        direction = 'toUMA'

    # Save request parameters
    context.user_data['MR_dir'] = direction
    context.user_data['MR_date'] = date
    context.user_data['MR_key'] = req_key

    keyboard = [[InlineKeyboardButton("✔️ Sí, eliminar", callback_data=ccd(cdh,"CANCEL_CONFIRM")),
                 ikbs_back_MR[0][0]]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Vas a eliminar la siguiente petición de viaje:\n\n"
    text += get_formatted_request(direction, date, req_key)
    text += f"\n\n¿Estás seguro?"
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return MR_EXECUTE

def MR_execute_action(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the MR_execute_action function.')

    # Obtain request parameters
    direction = context.user_data.pop('MR_dir')
    date = context.user_data.pop('MR_date')
    req_key = context.user_data.pop('MR_key')

    # Check action to execute
    if data[1] == "CANCEL_CONFIRM":
        delete_request(direction, date, req_key)
        text = escape_markdown(f"Tu petición de viaje ha sido anulado correctamente.",2)

    # Remove elements from user's dictionary
    for key in list(context.user_data.keys()):
        if key.startswith('MR_'):
            del context.user_data[key]

    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

def MR_end(update, context):
    """Ends my requests conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('MR_'):
            del context.user_data[key]
    query.edit_message_reply_markup(None)
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for 'my requests'
    ny_requests_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('mispeticiones', my_requests)],
        states={
            MR_SELECT: [
                CallbackQueryHandler(choose_request, pattern=f"^{ccd(cdh,'CANCEL')}$")
            ],
            MR_CANCEL: [
                CallbackQueryHandler(cancel_request, pattern=f"^{ccd(cdh,'ID','.*')}")
            ],
            MR_EXECUTE: [
                CallbackQueryHandler(MR_execute_action, pattern=f"^{ccd(cdh,'CANCEL_CONFIRM')}$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(my_requests_restart, pattern=f"^{ccd(cdh,'BACK')}$"),
                   CallbackQueryHandler(MR_end, pattern=f"^{ccd(cdh,'END')}$"),
                   CommandHandler('mispeticiones', my_requests)],
    )

    dispatcher.add_handler(ny_requests_conv_handler)
