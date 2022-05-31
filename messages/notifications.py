import logging, telegram, math
from os import environ
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from telegram.utils.helpers import escape_markdown
from datetime import datetime
from data.database_api import (is_driver, delete_user, delete_driver,
                                get_trips_by_driver, get_trip_passengers,
                                get_trip_time, delete_trip, remove_passenger,
                                get_slots, get_fee,
                                get_users_for_offer_notification,
                                get_users_for_request_notification,
                                get_requests_by_date_range)
from messages.format import (get_formatted_trip_for_passenger,
                            format_trip_from_data, format_request_from_data)
from messages.message_queue import send_message
from utils.common import *

logger = logging.getLogger(__name__)

def notify_new_trip(context, trip_key, direction, chat_id, date, time, slots=None, fee=None):
    if not slots:
        slots = get_slots(chat_id)
    if not fee:
        fee = get_fee(chat_id)

    text = "🔵 Se ha publicado un *nuevo viaje*:\n\n"
    text += format_trip_from_data(direction, date, chat_id, time, slots, fee=fee)
    text_general = f"{text}\n\nSi te interesa reservar un asiento, puedes"\
                   f" hacerlo a través del comando /verofertas\."

    # Obtain list of interested users for this trip
    weekday = weekdays[datetime.fromisoformat(date).weekday()]
    user_ids = get_users_for_offer_notification(direction, weekday, time)
    # Make sure that the driver doesn't get notified
    user_ids = list(set(user_ids)-set([str(chat_id)]))

    # Now get the possible users requesting a trip similar to this one
    time_before, time_after = get_time_range_from_center_time(time, 1)
    req_dict = get_requests_by_date_range(direction, date, time_before, time_after)
    if req_dict:
        req_user_ids = [str(req_dict[key]['Chat ID']) for key in req_dict]
        # Make sure that the driver doesn't get notified
        req_user_ids = list(set(req_user_ids)-set([str(chat_id)]))
        # Don't send general notifications to users that will receive the request-type one
        user_ids = list(set(user_ids)-set(req_user_ids))
        # Send a more convenient message to those who are requesting a trip
        # with similar characteristics to this one
        text_req = f"{text}\n\nComo has pedido un viaje con características"\
                   f" similares, puedes mandar una solicitud de reserva"\
                   f" directamente desde este mensaje:"
        cbd = "RSV"
        keyboard = [[InlineKeyboardButton("Solicitar reserva",
                        callback_data=ccd(cbd, direction[2:5].upper(), date, trip_key)),
                     InlineKeyboardButton("❌ Descartar",
                        callback_data=ccd(cbd, "DISMISS"))]]
        send_message(context, req_user_ids, text_req, telegram.ParseMode.MARKDOWN_V2,
                        reply_markup=InlineKeyboardMarkup(keyboard))

    # Send general notification to the rest of users
    send_message(context, user_ids, text_general, telegram.ParseMode.MARKDOWN_V2)

def notify_new_request(context, direction, chat_id, date, time):
    text = "🔴 Se ha publicado una *nueva petición* de viaje:\n\n"
    text += format_request_from_data(direction, date, chat_id, time)
    text2 = f"\n\nSi estás interesado en publicar una oferta para satisfacer"\
            f" esta petición, puedes hacerlo a través del comando /nuevoviaje."\
            f"\nTambién puedes escribirle directamente al solicitante pulsando"\
            f" en su nombre (pero si no publicas el viaje, nadie más se"\
            f" enterará de que lo vas a hacer)."
    text += escape_markdown(text2, 2)

    # Obtain list of interested drivers for this request
    weekday = weekdays[datetime.fromisoformat(date).weekday()]
    user_ids = get_users_for_request_notification(direction, weekday)

    # Make sure that the requester doesn't get notified
    user_ids = list(set(user_ids)-set([str(chat_id)]))

    send_message(context, user_ids, text, telegram.ParseMode.MARKDOWN_V2)

def delete_trip_notify(update, context, direction, date, key):
    # Notify possible passengers
    passenger_ids = get_trip_passengers(direction, date, key)

    if passenger_ids:
        text_passenger = f"🚫 El siguiente viaje, en el que te habían "\
                         f"aceptado como pasajero, ha sido anulado:\n\n"
        text_passenger = escape_markdown(text_passenger,2)
        text_passenger += get_formatted_trip_for_passenger(direction, date, key)
        send_message(context, passenger_ids, text_passenger,
                            telegram.ParseMode.MARKDOWN_V2,
                            notify_id=update.effective_chat.id)

    delete_trip(direction, date, key)

def remove_passenger_notify(update, context, passenger_id, direction, date, key):
    remove_passenger(passenger_id, direction, date, key)
    # Notify user
    text_passenger = f"🚫 Has sido expulsado del siguiente viaje:\n\n"
    text_passenger += get_formatted_trip_for_passenger(direction, date, key)
    send_message(context, passenger_id, text_passenger,
                        telegram.ParseMode.MARKDOWN_V2,
                        notify_id=update.effective_chat.id)

def delete_driver_notify(update, context, chat_id):
    week_strings = week_isoformats()
    trips_dict = get_trips_by_driver(chat_id, week_strings[0], week_strings[-1])

    # Notify possible passengers
    if trips_dict:
        send_message(context, chat_id, "Anulando todos los viajes pendientes")
        for dir in trips_dict:
            for date in trips_dict[dir]:
                for key in trips_dict[dir][date]:
                    # If trip has already ocurred, don't notify users
                    if not (date==week_strings[0] and
                        not is_future_datetime(date, get_trip_time(dir, date, key))):
                        passenger_ids = get_trip_passengers(dir, date, key)
                        if passenger_ids:
                            text_passenger = f"🚫 El siguiente viaje, en el que te habían "\
                                             f"aceptado como pasajero, ha sido anulado:\n\n"
                            text_passenger = escape_markdown(text_passenger,2)
                            text_passenger += get_formatted_trip_for_passenger(dir, date, key)
                            send_message(context, passenger_ids, text_passenger,
                                                telegram.ParseMode.MARKDOWN_V2,
                                                notify_id=update.effective_chat.id)

    # This function already deletes all the trips
    delete_driver(chat_id)

def delete_user_notify(update, context, chat_id):
    if is_driver(chat_id):
        delete_driver_notify(update, context, chat_id)
    delete_user(chat_id)

def debug_group_notify(context, text, parse_mode=None):
    if "DEBUG_GROUP_CHAT_ID" in environ:
        send_message(context, environ["DEBUG_GROUP_CHAT_ID"], text, parse_mode)
