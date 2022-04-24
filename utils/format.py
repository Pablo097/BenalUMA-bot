import logging
import re
from data.database_api import (get_name, is_driver, get_slots, get_car,
                                get_fee, get_bizum, get_trip, get_trips_by_date_range)
from telegram.utils.helpers import escape_markdown
from utils.common import *

def get_formatted_user_config(chat_id):
    """Generates a formatted string with the user configuration.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    string
        Formatted string with user's configuration in Telegram's Markdown v2.

    """
    string = f"💬 *Nombre*: `{escape_markdown(get_name(chat_id),2)}`"
    role = 'Conductor' if is_driver(chat_id) else 'Pasajero'
    string += f"\n🧍 *Rol*: `{role}`"

    if role == 'Conductor':
        string += f"\n💺 *Asientos disponibles*: `{str(get_slots(chat_id))}`"
        string += f"\n🚘 *Descripción vehículo*: `{escape_markdown(get_car(chat_id),2)}`"
        fee = get_fee(chat_id)
        if fee != None:
            string += f"\n🪙 *Pago por trayecto*: `{str(fee).replace('.',',')}€`"
        bizum = get_bizum(chat_id)
        if bizum == True:
            string += f"\n💸 `Aceptas Bizum`"
        elif bizum == False:
            string += f"\n💸🚫 `NO aceptas Bizum`"

    return string

def format_trip_from_data(direction=None, date=None, chat_id=None, time=None,
                        slots=None, car=None, fee=None, passenger_ids=None):
    """Generates formatted string with the given trip data.
    All the parameters are optional.
    This function formats the data as it is passed.
    Only the users' names are obtained from their chat IDs.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    chat_id : int
        Telegram Chat ID of the driver.
    time : string
        Departure time with ISO format 'HH:MM'.
    slots : int
        Number of available slots for this specific trip.
    car : string
        Description of the driver's car.
    fee : float
        The per-user payment quantity.
    passenger_ids : list of ints
        Telegram Chat IDs of the accepted passengers in the trip.

    Returns
    -------
    string
        Formatted string in Telegram's Markdown v2.

    """
    string = ""

    if chat_id:
        driver = escape_markdown(get_name(chat_id),2)
        string += f"🧑 *Conductor*: [{driver}](tg://user?id={str(chat_id)})\n"
    if direction:
        string += f"📍 *Dirección*: `{direction[2:]}`\n"
    if date:
        string += f"📅 *Fecha*: `{date[8:10]}/{date[5:7]}`\n"
    if time:
        string += f"🕖 *Hora*: `{time}`\n"
    if slots:
        string += f"💺 *Asientos disponibles*: `{str(slots)}`\n"
    if car:
        string += f"🚘 *Descripción vehículo*: `{escape_markdown(get_car(chat_id),2)}`\n"
    if fee:
        string += f"🪙 *Precio*: `{str(fee).replace('.',',')}€`\n"
    if passenger_ids:
        passenger_strings = [f"[{escape_markdown(get_name(id),2)}](tg://user?id={str(id)})"
                                                    for id in passenger_ids]
        string += f"👥 *Pasajeros aceptados*: {', '.join(passenger_strings)}\n"

    if string:
        # Remove last line break
        string = string[:-1]

    return string

def get_formatted_trip_for_driver(direction, date, key):
    """Generates a formatted string with the trip information interesting
    for the driver.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'
    key : type
        Unique key of the trip in the DB.

    Returns
    -------
    string
        Formatted string with trip's info in Telegram's Markdown v2.

    """

    trip_dict = get_trip(direction, date, key)

    time = trip_dict['Time']
    slots = trip_dict['Slots'] if 'Slots' in trip_dict else None
    fee = trip_dict['Fee'] if 'Fee' in trip_dict else None
    passengers_list = trip_dict['Passengers'] if 'Passengers' in trip_dict else None
    # if passengers_list and slots:
    #     slots -= len(passengers_list)

    return format_trip_from_data(direction, date, None, time, slots,
                                fee=fee, passenger_ids=passengers_list)

def get_formatted_trip_for_passenger(direction, date, key):
    """Generates a formatted string with the trip information interesting
    for the passenger.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'
    key : type
        Unique key of the trip in the DB.

    Returns
    -------
    string
        Formatted string with trip's info in Telegram's Markdown v2.

    """

    trip_dict = get_trip(direction, date, key)

    time = trip_dict['Time']
    driver_id = trip_dict['Chat ID']
    slots = trip_dict['Slots'] if 'Slots' in trip_dict else get_slots(driver_id)
    fee = trip_dict['Fee'] if 'Fee' in trip_dict else get_fee(driver_id)
    car = get_car(driver_id)
    if 'Passengers' in trip_dict:
        slots -= len(trip_dict['Passengers'])

    return format_trip_from_data(direction, date, driver_id, time, slots, car, fee)

def get_formatted_offered_trips(direction, date, time_start=None, time_stop=None):
    """Generates a formatted string with the offered trips in the
    time range, or in the whole day if no times given.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    time_start : string
        Range's start time with ISO format 'HH:MM'.
    time_stop : string
        Range's stop time with ISO format 'HH:MM'.

    Returns
    -------
    (string, list of strings)
        Formatted string in Telegram's Markdown v2, and a list of the trips'
        unique key IDs.


    """
    trips_dict = get_trips_by_date_range(direction, date, time_start, time_stop)
    trips_strings = []
    index = 1

    string = ""
    key_list = []
    if trips_dict:
        for key in trips_dict:
            if 'Slots' in trips_dict[key]:
                slots = trips_dict[key]['Slots']
            else:
                slots = get_slots(trips_dict[key]['Chat ID'])
            # Check if there are available seats yet
            if 'Passengers' in trips_dict[key]:
                slots -= len(trips_dict[key]['Passengers'])

            if slots > 0: # If trip is full, it is not shown
                if 'Fee' in trips_dict[key]:
                    fee = trips_dict[key]['Fee']
                else:
                    fee = get_fee(trips_dict[key]['Chat ID'])

                separator = escape_markdown("———————",2)
                # separator = escape_markdown("‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ‎ ",2)
                string += f"{separator} *Opción {str(index)}* {separator}\n"
                string += format_trip_from_data(chat_id=trips_dict[key]['Chat ID'],
                                                time=trips_dict[key]['Time'],
                                                slots=slots, fee=fee)
                string += "\n\n"
                index += 1
                key_list.append(key)

        # separator = f"\n--------------------------------"\
        #             f"--------------------------------\n"
        # string = escape_markdown(separator,2).join(trips_strings)

    else:
        string = "No existen viajes ofertados en las fechas seleccionadas\. 😔"

    return string, key_list
