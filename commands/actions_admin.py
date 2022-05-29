import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (is_registered, is_driver, ban_user, is_banned,
                                unban_user, get_chat_id_from_tg_username,
                                get_all_chat_ids)
from messages.format import get_formatted_user_config
from messages.notifications import delete_driver_notify, delete_user_notify
from messages.message_queue import send_message
from utils.common import *
from utils.decorators import admin

logger = logging.getLogger(__name__)

@admin
def ban(update, context):
    """Bans a user given its chat ID or telegram username as a command parameter"""
    if not context.args or len(context.args)!=1:
        text = "Sintaxis incorrecta\. Uso: `/ban <user_id/@username\>`"
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return

    user_id = context.args[0]
    if user_id[0]=='@':     # If the Telegram username is given
        username = user_id
        # Trust that the user has not changed its Telegram username since
        # the registration...
        user_id = get_chat_id_from_tg_username(username)
        if not user_id:
            text = f"No se ha encontrado ningún usuario registrado con este"\
                   f" nombre de usuario."
            update.message.reply_text(text)
            return
    elif not is_registered(user_id):
        text = "No se ha encontrado ningún usuario registrado con este ID."
        update.message.reply_text(text)

    if is_banned(user_id):
        text = f"El usuario con ID `{user_id}` ya está baneado\."
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return

    ban_user(user_id)
    text_user = f"⛔ Has sido baneado. Tu cuenta se ha eliminado y no puedes"\
                f" volver a usar el bot."
    send_message(context, user_id, text_user)
    text = f"El usuario con ID `{user_id}` ha sido baneado\."
    update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return

@admin
def unban(update, context):
    """Unbans a user given its chat ID as a command parameter"""
    if not context.args or len(context.args)!=1:
        text = "Sintaxis incorrecta\. Uso: `/unban <user_id\>`"
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return

    user_id = context.args[0]
    if user_id[0]=='@':     # If the Telegram username is given
        text = f"No se aceptan nombres de usuario de Telegram para este comando,"\
               f" solo sus IDs."
        update.message.reply_text(text)
        return
    if not is_banned(user_id):
        text = f"El usuario con ID `{user_id}` no está baneado\."
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return

    unban_user(user_id)
    text_user = f"🆗 Has sido desbaneado. Puedes volver a crearte una cuenta"\
                f" si lo deseas."
    send_message(context, user_id, text_user)
    text = f"El usuario con ID `{user_id}` ha sido desbaneado\."
    update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return

@admin
def broadcast(update, context):
    if not context.args:
        text = "Sintaxis incorrecta\. Uso: `/broadcast <mensaje\>`"
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return

    # message = ' '.join(context.args)
    message = update.message.text.split(" ",1)[1]
    send_message(context, get_all_chat_ids(), message)
    
    return

def add_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("ban", ban))
    dispatcher.add_handler(CommandHandler("unban", unban))
    dispatcher.add_handler(CommandHandler("broadcast", broadcast))
