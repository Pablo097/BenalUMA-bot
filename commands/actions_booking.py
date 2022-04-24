import logging
import telegram
from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from utils.common import *
from utils.format import get_formatted_trip_for_passenger, get_formatted_trip_for_driver
from data.database_api import get_trip, get_slots, add_passenger

def alert_user(context, update):
    query = update.callback_query
    query.answer()

    driver_id = update.effective_chat.id
    data = scd(query.data)
    if data[0] != 'ALERT_USER':
        raise SyntaxError('This callback data does not belong to the alert_user function.')

    action, user_id, dir, date = data[1:5]
    trip_key = ';'.join(data[5:])   # Just in case the unique ID constains a ';'

    if action == "CONFIRM":
        trip_dict = get_trip(dir, date, trip_key)
        slots = trip_dict['Slots'] if 'Slots' in trip_dict else get_slots(driver_id)
        if 'Passengers' in trip_dict:
            slots -= len(trip_dict['Passengers'])
            is_already_passenger = str(user_id) in trip_dict['Passengers']

        if slots > 0: # If trip is not full, it accepts the passenger
            if not is_already_passenger: # Confirm passenger
                add_passenger(user_id, dir, date, trip_key)
                text = escape_markdown("¡Hecho! Tienes una nueva plaza reservada.\n\n",2)
                text += get_formatted_trip_for_driver(dir, date, key)
                text_booker = f"¡Enhorabuena! Te han confirmado la reserva para "\
                              f"el siguiente viaje.\n\n"
            else:
                text = f"⚠️ No puedes aceptar a este usuario porque ya es un"\
                       f" pasajero confirmado para este viaje."
                text = escape_markdown(text,2)
                text_booker = ""
        else:
            text = f"⚠️ Atención, no te quedan plazas para este viaje. No es "\
                   f"posible confirmar esta reserva."
            text = escape_markdown(text,2)
            text_booker = f"⚠️ Atención, no se ha podido confirmar la reserva "\
                          f"porque no quedan más plazas libres. Contacta con el "\
                          f"conductor pulsando sobre su nombre si quieres "\
                          f"preguntarle sobre la disponibilidad.\n\n"

    if action == "REJECT":
        text = escape_markdown("🚫 Has rechazado la petición de reserva.",2)
        text_booker = f"❌ Tu petición de reserva para el siguiente viaje ha"\
                      f" sido rechazada.\n\n"


    # Send messages
    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    if text_booker:
        text_booker = escape_markdown(text_booker,2)
        text_booker += get_formatted_trip_for_passenger(dir, date, key)
        context.bot.send_message(user_id, text_booker,
                                    parse_mode=telegram.ParseMode.MARKDOWN_V2)


def add_handlers(dispatcher):
    # Create Callback Query handler for 'alert user'
    dispatcher.add_handler(CallbackQueryHandler(alert_user, pattern='^ALERT_USER.*'))
