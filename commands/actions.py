import logging, telegram
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from data.database_api import add_user, add_driver, is_registered, is_driver, set_fee
from utils.common import *

REG_NAME, REG_USAGE, REG_SLOTS, REG_CAR = range(4)

def start(update, context):
    if update.message.chat.type == "private":
        text = f"🚗 ¡Bienvenido al bot de BenalUMA! 🚗"\
               f"\n\nPara comenzar, escribe /registro para registrarte en el sistema"\
               f" o /help para ver los comandos disponibles."
        update.message.reply_text(text)
    else:
        text = f"Para comenzar, escríbeme un mensaje privado a @BenalUMA_bot"
        update.message.reply_text(text)

def help(update, context):
    if update.message.chat.type == "private":
        text = f"Comandos disponibles:"

        if is_registered(update.effective_chat.id):
            text += f"\n⚙️ /config - Accede a las opciones de configuración de tu cuenta."
            text += f"\n📚 /verofertas - Mostrar viajes ofertados que cumplan los criterios indicados."
            if is_driver(update.effective_chat.id):
                text += f"\n🏁 /nuevoviaje - Inicia el asistente para crear una nueva"\
                        f" oferta de viaje."
                text += f"\n📆 /misviajes - Muestra los viajes que tienes ofertados"\
                        f" para esta semana."
        else:
            text += f"\n🔑 /registro - Comienza a usar BenalUMA registrándote en el sistema."

        update.message.reply_text(text)
    else:
        update.message.reply_text(f"Para información, escríbeme un mensaje privado a @BenalUMA_bot.")

def register(update, context):
    """Starts the register conversation process"""
    if is_registered(update.effective_chat.id):
        text = f"Ya te has registrado en el sistema."
        update.message.reply_text(text)
        return ConversationHandler.END
    else:
        text = f"Antes de registrarte, asegúrate de unirte al grupo de BenalUMA "\
               f"y conocer las normas de uso. Envía /cancelar para cancelar el registro."
        update.message.reply_text(text)
        text = f"Introduzca su nombre y apellidos, los cuales serán mostrados a los "\
               f"demás usuarios."
        update.message.reply_text(text)
        return REG_NAME

def register_name(update, context):
    """Stores username into DB and asks for their typical usage"""
    add_user(update.effective_chat.id, update.message.text)

    reply_keyboard = [["Conduzco"], ["Pido coche"]]
    text = f"Tu nombre ha sido guardado con éxito."\
           f"\nIndica ahora si normalmente llevas o pides coche."
    update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(
        reply_keyboard, one_time_keyboard=True, input_field_placeholder='Normalmente...'
    ))

    return REG_USAGE

def register_usage(update, context):
    """Checks user typical usage and continues conversation if necessary"""
    if update.message.text == 'Conduzco':
        reply_keyboard = [[1,2,3], [4,5,6]]
        text = f"Indica ahora cuántos asientos disponibles sueles ofertar."
        update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True,
            input_field_placeholder='Número de asientos'))
        return REG_SLOTS
    else:
        text = f"Te has registrado correctamente. \n¡Ya puedes empezar a usar el bot!"
        update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())
        text = f"Un aviso antes de que empieces a ofertar/reservar viajes:\nEste"\
               f" bot necesita poder enlazar a tu perfil para que los demás"\
               f" usuarios puedan contactar contigo por privado en caso de que"\
               f" sea necesario (por ejemplo, para tratar detalles más específi"\
               f"cos del trayecto).\nPara asegurarte de que el bot puede hacerlo"\
               f" correctamente, por favor, comprueba que en los ajustes de Telegram,"\
               f" en **'Privacidad y Seguridad' > 'Mensajes reenviados'**, tengas"\
               f" marcada la opción __Todos__ o, al menos, añadas este bot como "\
               f" excepción.\n¡Buen viaje! "
        update.message.reply_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return ConversationHandler.END

def register_slots(update, context):
    """Stores user slots and continues conversation"""
    context.user_data['slots'] = update.message.text

    text = f"Finalmente, indica el modelo y color de tu coche para facilitar a "\
           f"los pasajeros reconocerlo cuando los recojas."
    update.message.reply_text(text, reply_markup=ReplyKeyboardRemove())

    return REG_CAR

def register_car(update, context):
    """Stores driver info into DB and ends the conversation"""
    slots = int(context.user_data['slots'])
    car = update.message.text
    context.user_data.clear()
    add_driver(update.effective_chat.id, slots, car)
    set_fee(update.effective_chat.id, MAX_FEE)

    text = f"Te has registrado correctamente. Se te ha configurado un precio"\
           f" por trayecto de {str(MAX_FEE).replace('.',',')}€ por defecto."\
           f" Puedes cambiar esto y más ajustes con el comando /config."
    update.message.reply_text(text)
    update.message.reply_text("¡Ya puedes empezar a usar el bot!")

    return ConversationHandler.END

def register_cancel(update, context):
    """Cancels registration and ends the conversation."""
    update.message.reply_text(
        'Has cancelado el proceso de registro.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def add_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))

    # Add register conversation handler
    reg_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('registro', register)],
        states={
            REG_NAME: [MessageHandler(Filters.text & ~Filters.command, register_name)],
            REG_USAGE: [MessageHandler(Filters.regex('^(Conduzco|Pido coche)$'),
                                    register_usage)],
            REG_SLOTS: [
                MessageHandler(Filters.regex('^(1|2|3|4|5|6)$'), register_slots),
            ],
            REG_CAR: [MessageHandler(Filters.text & ~Filters.command, register_car)],
        },
        fallbacks=[CommandHandler('cancelar', register_cancel)],
    )

    dispatcher.add_handler(reg_conv_handler)
