from os import environ
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from commands import actions
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
    firebase_admin.credentials.Certificate(ENV_KEYS),
    {'databaseURL': environ["FIREBASE_DATABASE_URL"]}
)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

NAME, USAGE, SLOTS, CAR = range(4)

# Define a few command handlers. These usually take the two arguments update and
# context. Error handlers also receive the raised TelegramError object in error.
def echo(update, context):
    """Echo the user message."""
    update.message.reply_text(update.message.text)

def record(update, context):
    """Logs message into database."""
    ref = db.reference('/Users/'+str(update.effective_chat.id))
    ref.update({"message": ' '.join(context.args)})

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main(webhook_flag = True):
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", actions.start))
    dp.add_handler(CommandHandler("help", actions.help))
    dp.add_handler(CommandHandler("record", record))

    # Add register conversation handler
    reg_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registro', actions.register)],
        states={
            NAME: [MessageHandler(Filters.text & ~Filters.command, actions.register_name)],
            USAGE: [MessageHandler(Filters.regex('^(Conduzco|Pido coche)$'),
                                    actions.register_usage)],
            SLOTS: [
                MessageHandler(Filters.regex('^(1|2|3|4|5|6)$'), actions.register_slots),
            ],
            CAR: [MessageHandler(Filters.text & ~Filters.command, actions.register_car)],
        },
        fallbacks=[CommandHandler('cancelar', actions.register_cancel)],
    )

    dp.add_handler(reg_conv_handler)

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    if webhook_flag:
        updater.start_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TOKEN,
            webhook_url='https://' + NAME + '.herokuapp.com/' + TOKEN
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
