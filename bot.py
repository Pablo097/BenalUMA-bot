import logging, firebase_admin, json
from os import environ
from firebase_admin import db
from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, CallbackContext,
                            Filters, TypeHandler, DispatcherHandlerStop)
from commands import (actions, actions_config, actions_trip, actions_booking,
                      actions_mytrips, actions_mybookings, actions_notifications,
                      actions_request, actions_seerequests, actions_myrequests,
                      actions_admin)
from data.database_api import is_banned
from time import time

PORT = int(environ.get('PORT', '8443'))
TOKEN = environ["TOKEN"]
NAME = 'benaluma-bot'

ENV_KEYS = {
    "type": "service_account",
    "project_id": environ["FIREBASE_PROJECT_ID"],
    "private_key_id": environ["FIREBASE_PRIVATE_KEY_ID"],
    "private_key": environ["FIREBASE_PRIVATE_KEY"].replace("\\n", "\n"),
    "client_email": environ["FIREBASE_CLIENT_EMAIL"],
    "client_id": environ["FIREBASE_CLIENT_ID"],
    "token_uri": environ["FIREBASE_TOKEN_URI"],
}

# Setup Firebase database
firebase_admin.initialize_app(
    firebase_admin.credentials.Certificate(ENV_KEYS),
    {'databaseURL': environ["FIREBASE_DATABASE_URL"]}
)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

def text_handler(update, context):
    """Answers to a text message"""
    text = f"¡Hola! Si no sabes cómo usar este bot, manda el comando /help"\
           f" (puedes pulsar sobre el comando para que se envíe automáticamente)."\
           f"\n\nPor favor, no me uses como tu basurero personal de mensajes,"\
           f" ya que en tal caso podrías ser baneado."
    update.message.reply_text(text)

def callback(update, context):
    """Checks whether user is banned to let they use the bot or not.
    Also checks if the message comes from a private conversation or the debug group"""
    # Check banned users
    if is_banned(update.effective_chat.id):
        restrict_until = context.user_data.get("restrictUntil", 0)
        if restrict_until:
            if time() > restrict_until:
                context.user_data["restrictUntil"] = time() + 60*5 # 5 minutes
                update.effective_message.reply_text("Estás baneado. No puedes usar el bot.")
        else:
            update.effective_message.reply_text("Estás baneado. No puedes usar el bot.")
        raise DispatcherHandlerStop
    # Check private chats
    if update.effective_chat.type != 'private':
        if not ("DEBUG_GROUP_CHAT_ID" in environ and
                str(update.effective_chat.id)==str(environ["DEBUG_GROUP_CHAT_ID"])):
            text = "Para usarme, escríbeme un mensaje privado a @BenalUMA_bot."
            update.message.reply_text(text)
            raise DispatcherHandlerStop

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main(webhook_flag = True):
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add a handler in a higher priority group to avoid banned users from using the bot
    handler = TypeHandler(Update, callback)
    dp.add_handler(handler, -1)

    # log all errors
    dp.add_error_handler(error)

    # Add general actions (start, help, register)
    actions.add_handlers(dp)

    # Add administrator actions (ban, unban, broadcast)
    actions_admin.add_handlers(dp)

    # Add configuration actions
    actions_config.add_handlers(dp)

    # Add trip actions
    actions_trip.add_handlers(dp)

    # Add booking actions
    actions_booking.add_handlers(dp)

    # Add my trips actions
    actions_mytrips.add_handlers(dp)

    # Add my bookings actions
    actions_mybookings.add_handlers(dp)

    # Add request actions
    actions_request.add_handlers(dp)

    # Add see request actions
    actions_seerequests.add_handlers(dp)

    # Add see request actions
    actions_myrequests.add_handlers(dp)

    # Add notifications actions
    actions_notifications.add_handlers(dp)

    # Default handler when no coherent text is received
    dp.add_handler(MessageHandler(Filters.text, text_handler))

    # Start the Bot
    if webhook_flag:
        updater.start_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TOKEN,
            webhook_url=f"https://{NAME}.onrender.com/{TOKEN}"
        )
    else:
        # For local development purposes
        updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
