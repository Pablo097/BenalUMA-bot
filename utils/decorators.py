import logging
from os import environ
from functools import wraps
from telegram import Update, ChatAction
from telegram.ext import CallbackContext
from data.database_api import is_registered, is_driver

def registered(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if not is_registered(update.effective_user.id):
            text = f"Antes de poder usar este comando debes registrarte con el comando /registro."
            update.effective_message.reply_text(text)
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def driver(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if not is_driver(update.effective_user.id):
            text = f"Para poder usar este comando debes tener rol de conductor. "\
                   f"Puedes cambiar tu rol a través del comando /config."
            update.effective_message.reply_text(text)
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def send_typing_action(func):
    """Sends typing action while processing func command."""
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(chat_id=update.effective_message.chat_id,
                                        action=ChatAction.TYPING)
        return func(update, context,  *args, **kwargs)

    return command_func

def admin(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        if str(update.effective_user.id)!=str(environ["ADMIN_CHAT_ID"]):
            text = f"Para poder usar este comando debes ser administrador."
            update.effective_message.reply_text(text)
            return
        return func(update, context, *args, **kwargs)
    return wrapped
