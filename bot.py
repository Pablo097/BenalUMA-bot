import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from os import environ
import firebase_admin
from firebase_admin import db
import json

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
    credentials.Certificate(ENV_KEYS),
    {'databaseURL': environ["FIREBASE_DATABASE_URL"]}
)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')

def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')

def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def record(update, context):
    """Logs message into database."""
    ref = db.reference(str(update.effective_chat.id))
    ref.set({"message": update.message.text})

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("record", record))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_webhook(
        listen="0.0.0.0",
        port=int(PORT),
        url_path=TOKEN,
        webhook_url='https://' + NAME + '.herokuapp.com/' + TOKEN
    )

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
