import logging
import re
from datetime import datetime
from data.database_api import (get_name, is_driver, get_slots, get_car,
                               get_fee, get_bizum, get_trip,
                               get_trips_by_date_range, get_trips_by_driver,
                               get_trips_by_passenger,
                               get_offer_notification_by_user)
from telegram.utils.helpers import escape_markdown
from utils.common import *

def get_markdown2_inline_mention(chat_id):
    name = get_name(chat_id)
    if not name:
        name = str(chat_id)
    return f"[{escape_markdown(name,2)}](tg://user?id={chat_id})"

def get_formatted_user_config(chat_id):
    """Generates a formatted string with the user configuration.

    Parameters
    ----------
    chat_id : int or str
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
            string += f"\n💰 *Precio por trayecto*: `{str(fee).replace('.',',')}€`"
        bizum = get_bizum(chat_id)
        if bizum == True:
            string += f"\n💳 `Aceptas Bizum`"
        elif bizum == False:
            string += f"\n💳🚫 `NO aceptas Bizum`"

    return string

def format_trip_from_data(direction=None, date=None, chat_id=None, time=None,
                          slots=None, car=None, fee=None, bizum=None,
                          passenger_ids=None, is_abbreviated=False):
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
    bizum : boolean
        Driver's Bizum preference flag.
    passenger_ids : list of ints
        Telegram Chat IDs of the accepted passengers in the trip.
    is_abbreviated : boolean
        Flag to indicate whether to abbreviate the message, only using
        the emojis and writting all in one line, without Markdown.

    Returns
    -------
    string
        Formatted string in Telegram's Markdown v2.

    """
    fields = []

    if not is_abbreviated:
        if chat_id:
            fields.append(f"🧑 *Conductor*: {get_markdown2_inline_mention(chat_id)}")
        if direction:
            fields.append(f"📍 *Dirección*: `{direction[2:]}`")
        if date:
            weekday = weekdays[datetime.fromisoformat(date).weekday()]
            fields.append(f"📅 *Fecha*: `{weekday} {date[8:10]}/{date[5:7]}`")
        if time:
            fields.append(f"🕖 *Hora*: `{time}`")
        if slots:
            fields.append(f"💺 *Asientos disponibles*: `{str(slots)}`")
        if car:
            fields.append(f"🚘 *Descripción vehículo*: `{escape_markdown(get_car(chat_id),2)}`")
        if fee:
            fields.append(f"💰 *Precio*: `{str(fee).replace('.',',')}€`")
        if bizum != None:
            fields.append(f"💳 *Bizum*: `{'Aceptado' if bizum else 'NO aceptado'}`")
        if passenger_ids:
            passenger_strings = [get_markdown2_inline_mention(id) for id in passenger_ids]
            fields.append(f"👥 *Pasajeros aceptados*: {', '.join(passenger_strings)}")
        string = '\n'.join(fields)
    else:
        if chat_id:
            fields.append(f"🧑 {get_name(chat_id)}")
        if direction:
            fields.append(f"📍 {direction[2:]}")
        if date:
            weekday = weekdays[datetime.fromisoformat(date).weekday()]
            fields.append(f"📅 {weekday} {date[8:10]}")
        if time:
            fields.append(f"🕖 {time}")
        if slots:
            fields.append(f"💺 {str(slots)}")
        if car:
            fields.append(f"🚘 {get_car(chat_id)}")
        if fee:
            fields.append(f"💰 {str(fee).replace('.',',')}€")
        if bizum != None:
            fields.append(f"💳 {'OK' if bizum else 'NO'}")
        if passenger_ids:
            passenger_strings = [get_name(id) for id in passenger_ids]
            fields.append(f"👥 {', '.join(passenger_strings)}")
        string = '  '.join(fields)

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

def get_formatted_trip_for_passenger(direction, date, key, is_abbreviated=True):
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
    is_abbreviated : boolean
        Flag indicating whether the string must be abbreviated or not.
        The abbreviated form does not include the car description nor the
        Bizum preference.

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
    car = get_car(driver_id) if not is_abbreviated else None
    bizum = get_bizum(driver_id) if not is_abbreviated else None
    if 'Passengers' in trip_dict:
        slots -= len(trip_dict['Passengers'])

    return format_trip_from_data(direction, date, driver_id, time,
                                slots, car, fee, bizum)

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
        Range's start time with ISO format 'HH:MM'. Optional
    time_stop : string
        Range's stop time with ISO format 'HH:MM'. Optional

    Returns
    -------
    (string, list of strings)
        Formatted string in Telegram's Markdown v2, and a list of the trips'
        unique key IDs.

    """
    trips_dict = get_trips_by_date_range(direction, date, time_start, time_stop)
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
    else:
        string = "No existen viajes ofertados en las fechas seleccionadas\."

    return string, key_list

def get_driver_week_formatted_trips(chat_id):
    """Generates a formatted string with the offered trips for the next
    week ahead from a given driver.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the driver.

    Returns
    -------
    (string, dict)
        Formatted string in Telegram's Markdown v2, and the dictionary with
        the week ahead trips ordered by date.

    """
    week_strings = week_isoformats()
    weekday_strings = weekdays_from_today()
    trips_dict = get_trips_by_driver(chat_id, week_strings[0], week_strings[-1], True)

    string = ""
    if trips_dict:
        for date in trips_dict:
            # Format string with trips
            header = f"*{weekday_strings[week_strings.index(date)]} "\
                     f"{date[8:10]}/{date[5:7]}*"
            sep_length = int(13-len(header)/2)
            string += f"{'—'*5} {header} {'—'*sep_length}\n\n"
            for key in trips_dict[date]:
                trip = trips_dict[date][key]
                direction = trip['Direction']
                time = trip['Time']
                slots = trip['Slots'] if 'Slots' in trip else None
                fee = trip['Fee'] if 'Fee' in trip else None
                passengers_list = trip['Passengers'] if 'Passengers' in trip else None
                string += format_trip_from_data(direction, time=time, slots=slots,
                                    fee=fee, passenger_ids=passengers_list)
                string += "\n\n"

    return string, trips_dict

def get_user_week_formatted_bookings(chat_id):
    """Generates a formatted string with the booked trips for the next
    week ahead from a given user.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.

    Returns
    -------
    (string, dict)
        Formatted string in Telegram's Markdown v2, and the dictionary with
        the week ahead bookings ordered by date.

    """
    week_strings = week_isoformats()
    weekday_strings = weekdays_from_today()
    trips_dict = get_trips_by_passenger(chat_id, week_strings[0], week_strings[-1], True)

    string = ""
    if trips_dict:
        for date in trips_dict:
            # Format string with trips
            header = f"*{weekday_strings[week_strings.index(date)]} "\
                     f"{date[8:10]}/{date[5:7]}*"
            sep_length = int(13-len(header)/2)
            string += f"{'—'*5} {header} {'—'*sep_length}\n\n"
            for key in trips_dict[date]:
                trip = trips_dict[date][key]
                driver_id = trip['Chat ID']
                direction = trip['Direction']
                time = trip['Time']
                fee = trip['Fee'] if 'Fee' in trip else get_fee(driver_id)
                slots = trip['Slots'] if 'Slots' in trip else get_slots(driver_id)
                if 'Passengers' in trip:
                    slots -= len(trip['Passengers'])
                    # Maybe it is also useful for passengers to see the other
                    # passengers in their booked trips?
                car = get_car(driver_id)
                bizum = get_bizum(driver_id)

                string += format_trip_from_data(direction, chat_id=driver_id,
                                            time=time, slots=slots, car=car,
                                            fee=fee, bizum=bizum)
                string += "\n\n"

    return string, trips_dict

def get_formatted_offers_notif_config(chat_id, direction=None):
    notif_dict = get_offer_notification_by_user(chat_id, direction)
    string = ""

    if not notif_dict:
        return string

    def format_dir(dir_notif_dict):
        string=""
        wd_string_list = []
        for weekday in dir_notif_dict:
            weekday_string = f"• *{'Cada día' if weekday=='All days' else weekdays[weekdays_en.index(weekday)]}*: "
            if dir_notif_dict[weekday] == True:
                weekday_string += f"Todas horas"
            else:
                start_hour = dir_notif_dict[weekday]['Start']
                end_hour = dir_notif_dict[weekday]['End']
                weekday_string += f"{start_hour:02}h-{end_hour:02}h"
            wd_string_list.append(weekday_string)
        if wd_string_list:
            string = "\n".join(wd_string_list)
        return string

    if not direction:
        dir_string_list = []
        dir_string = ""
        for dir in notif_dict:
            dir_string = f"Hacia {dir[2:]}:\n"
            dir_string += format_dir(notif_dict[dir])
            dir_string_list.append(dir_string)
        if dir_string_list:
            string = "\n\n".join(dir_string_list)
    else:
        string = format_dir(notif_dict)

    return string
