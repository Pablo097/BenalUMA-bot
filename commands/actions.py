import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from firebase_admin import db

REG_NAME, REG_USAGE, REG_SLOTS, REG_CAR = range(4)

def start(update, context):
    if update.message.chat.type == "private":
        text = ("¡Bienvenido al bot de BenalUMA! 🚗🚗"
                "\n\nPara comenzar, escribe /registro para registrarte en el sistema"
                " o /help para ver los comandos disponibles.")
        update.message.reply_text(text)
    else:
        text = "Para comenzar, escríbeme un mensaje privado a @BenalUMA_bot"
        update.message.reply_text(text)

def help(update, context):
    if update.message.chat.type == "private":
        text = "Comandos disponibles:"

        text += "\n🖊 /registro - Comienza a usar BenalUMA registrándote en el sistema."

        update.message.reply_text(text)
    else:
        update.message.reply_text("Para información, escríbeme un mensaje privado a @BenalUMA_bot.")

def register(update, context):
    """Starts the register conversation process"""
    text = ("Antes de registrarte, asegúrate de unirte al grupo de BenalUMA "
            "y conocer las normas de uso. Envía /cancelar para cancelar el registro.")
    update.message.reply_text(text)
    text = ("Introduzca su nombre y apellidos, los cuales serán mostrados a los "
            "demás usuarios.")
    update.message.reply_text(text)

    return REG_NAME

def register_name(update, context):
    """Stores username into DB and asks for their typical usage"""
    ref = db.reference('/Users/'+str(update.effective_chat.id))
    ref.set({"name": update.message.text})

    reply_keyboard = [["Conduzco", "Pido coche"]]
    text = ("Tu nombre ha sido guardado con éxito."
            "\n\nIndica ahora si normalmente llevas o pides coche.")
    update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Normalmente...'
    ))

    return REG_USAGE

def register_usage(update, context):
    """Stores user typical usage into DB and continues conversation if necessary"""
    if update.message.text == 'Conduzco':
        reply_keyboard = [list(range(1,6,1))]
        text = "Indica ahora cuántos asientos disponibles sueles ofertar."
        update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            input_field_placeholder='Número de asientos'))
        return REG_SLOTS
    else:
        text = "Te has registrado correctamente. \n¡Ya puedes empezar a usar el bot!"
        update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

def register_slots(update, context):
    """Stores user slots into DB and continues conversation"""
    ref = db.reference('/Drivers/'+str(update.effective_chat.id))
    ref.set({"slots": str(update.message.text)})

    text = ("Finalmente, indica el modelo y color de tu coche para facilitar a "
            "los pasajeros reconocerlo cuando los recojas.")
    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

    return REG_CAR

def register_car(update, context):
    """Stores user car into DB and ends the conversation"""
    ref = db.reference('/Drivers/'+str(update.effective_chat.id))
    ref.update({"car": update.message.text})

    text = "Te has registrado correctamente. \n¡Ya puedes empezar a usar el bot!"
    update.message.reply_text(text)

    return ConversationHandler.END

def register_cancel(update, context):
    """Cancels registration and ends the conversation."""
    update.message.reply_text(
        'Has cancelado el proceso de registro.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END
