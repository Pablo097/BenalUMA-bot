import logging, re
from data.database_api import (get_name, is_driver, get_slots, get_car,
                               get_fee, get_bizum, get_trip,
                               get_trips_by_date_range, get_trips_by_driver,
                               get_trips_by_passenger,
                               get_offer_notification_by_user,
                               get_request_notification_by_user,
                               get_request, get_requests_by_date_range,
                               get_requests_by_user)
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
        # if bizum == True:
        #     string += f"\n💳 `Aceptas Bizum`"
        # elif bizum == False:
        #     string += f"\n💳🚫 `NO aceptas Bizum`"
        if bizum != None:
            string += f"\n💳 *Bizum*: `{'P' if bizum else '🚫 NO p'}ermitido`"
        univ_name, home_name = list(dir_dict.values())
        home = get_home(chat_id)
        if home != None:
            string += f"\n🏠 *Zona {home_name}*: `{escape_markdown(home,2)}`"
        univ = get_univ(chat_id)
        if univ != None:
            string += f"\n🏢 *Zona {univ_name}*: `{escape_markdown(univ,2)}`"

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
            fields.append(f"📍 *Dirección*: `{dir_dict.get(direction, direction[2:])}`")
        if date:
            weekday = get_weekday_from_date(date)
            fields.append(f"📅 *Fecha*: `{weekday} {date[8:10]}/{date[5:7]}`")
        if time:
            text_aux=''
            if direction:
                if direction==list(dir_dict.keys())[0]:
                    text_aux = ' \(llegada\)'
                if direction==list(dir_dict.keys())[1]:
                    text_aux = ' \(salida\)'
            fields.append(f"🕖 *Hora{text_aux}*: `{time}`")
        if slots:
            fields.append(f"💺 *Asientos disponibles*: `{str(slots)}`")
        if car:
            fields.append(f"🚘 *Descripción vehículo*: `{escape_markdown(car,2)}`")
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
            fields.append(f"📍 {dir_dict.get(direction, direction[2:])}")
        if date:
            weekday = get_weekday_from_date(date)
            fields.append(f"📅 {weekday} {date[8:10]}")
        if time:
            fields.append(f"🕖 {time}")
        if slots:
            fields.append(f"💺 {str(slots)}")
        if car:
            fields.append(f"🚘 {escape_markdown(car,2)}")
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

    string_list = []
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
                text = f"{separator} *Opción {str(index)}* {separator}\n"
                text += format_trip_from_data(chat_id=trips_dict[key]['Chat ID'],
                                                time=trips_dict[key]['Time'],
                                                slots=slots, fee=fee)
                string_list.append(text)
                key_list.append(key)
                index += 1

    if string_list:
        string = '\n\n'.join(string_list)
    else:
        string = ''

    return string, key_list

def get_formatted_trips_near_request(direction, date, time):
    """Generates a formatted string with the offered trips around the time
    of the request being published.

    Parameters
    ----------
    direction : string
        Direction of the request. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    time : string
        Request's required time with ISO format 'HH:MM'.

    Returns
    -------
    string
        Formatted string in Telegram's Markdown v2.

    """
    time_before, time_after = get_time_range_from_center_time(time, 1)
    trips_dict = get_trips_by_date_range(direction, date, time_before, time_after)

    string_list = []
    # key_list = []
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

                string_list.append(format_trip_from_data(chat_id=trips_dict[key]['Chat ID'],
                                                time=trips_dict[key]['Time'],
                                                slots=slots, fee=fee))
                # key_list.append(key)

    if string_list:
        string = '\n\n'.join(string_list)
    else:
        string = ''

    return string #, key_list

def format_request_from_data(direction=None, date=None, chat_id=None, time=None,
                            is_abbreviated=False):
    """Generates formatted string with the given request data.
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
        Telegram Chat ID of the requester.
    time : string
        Departure time with ISO format 'HH:MM'.
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
            fields.append(f"🧑 *Solicitante*: {get_markdown2_inline_mention(chat_id)}")
        if direction:
            fields.append(f"📍 *Dirección*: `{dir_dict.get(direction, direction[2:])}`")
        if date:
            weekday = get_weekday_from_date(date)
            fields.append(f"📅 *Fecha*: `{weekday} {date[8:10]}/{date[5:7]}`")
        if time:
            text_aux=''
            if direction:
                if direction==list(dir_dict.keys())[0]:
                    text_aux = ' \(llegada\)'
                if direction==list(dir_dict.keys())[1]:
                    text_aux = ' \(salida\)'
            fields.append(f"🕖 *Hora{text_aux}*: `{time}`")
        string = '\n'.join(fields)
    else:
        if chat_id:
            fields.append(f"🧑 {get_name(chat_id)}")
        if direction:
            fields.append(f"📍 {dir_dict.get(direction, direction[2:])}")
        if date:
            weekday = get_weekday_from_date(date)
            fields.append(f"📅 {weekday} {date[8:10]}")
        if time:
            fields.append(f"🕖 {time}")
        string = '  '.join(fields)

    return string

def get_formatted_request(direction, date, key):
    """Generates a formatted string with the request information.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'
    key : type
        Unique key of the request in the DB.

    Returns
    -------
    string
        Formatted string with request's info in Telegram's Markdown v2.

    """
    req_dict = get_request(direction, date, key)

    time = req_dict['Time']
    user_id = req_dict['Chat ID']

    return format_request_from_data(direction, date, user_id, time)

def get_formatted_requests(direction, date, time_start=None, time_stop=None):
    """Generates a formatted string with the trip requests in the
    time range, or in the whole day if no times given.

    Parameters
    ----------
    direction : string
        Direction of the trip request. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    time_start : string
        Range's start time with ISO format 'HH:MM'. Optional
    time_stop : string
        Range's stop time with ISO format 'HH:MM'. Optional

    Returns
    -------
    (string, list of strings)
        Formatted string in Telegram's Markdown v2, and a list of the trip
        requests' unique key IDs.

    """
    reqs_dict = get_requests_by_date_range(direction, date, time_start, time_stop)
    index = 1

    string_list = []
    key_list = []
    if reqs_dict:
        for key in reqs_dict:
            separator = escape_markdown("———————",2)
            text = f"{separator} *Petición {str(index)}* {separator}\n"
            text += format_request_from_data(chat_id=reqs_dict[key]['Chat ID'],
                                            time=reqs_dict[key]['Time'])
            string_list.append(text)
            key_list.append(key)
            index += 1

    if string_list:
        string = '\n\n'.join(string_list)
    else:
        string = ''

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
    week_string_list = []
    if trips_dict:
        for date in trips_dict:
            # Format string with trips
            header = f"*{weekday_strings[week_strings.index(date)]} "\
                     f"{date[8:10]}/{date[5:7]}*"
            sep_length = int(13-len(header)/2)
            day_string_list = [f"{'—'*5} {header} {'—'*sep_length}"]
            for key in trips_dict[date]:
                trip = trips_dict[date][key]
                direction = trip['Direction']
                time = trip['Time']
                slots = trip['Slots'] if 'Slots' in trip else None
                fee = trip['Fee'] if 'Fee' in trip else None
                passengers_list = trip['Passengers'] if 'Passengers' in trip else None
                day_string_list.append(format_trip_from_data(direction,
                                            time=time, slots=slots, fee=fee,
                                            passenger_ids=passengers_list))
            week_string_list.append('\n\n'.join(day_string_list))
        string = '\n\n'.join(week_string_list)

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
    week_string_list = []
    if trips_dict:
        for date in trips_dict:
            # Format string with trips
            header = f"*{weekday_strings[week_strings.index(date)]} "\
                     f"{date[8:10]}/{date[5:7]}*"
            sep_length = int(13-len(header)/2)
            day_string_list = [f"{'—'*5} {header} {'—'*sep_length}"]
            for key in trips_dict[date]:
                trip = trips_dict[date][key]
                driver_id = trip['Chat ID']
                direction = trip['Direction']
                time = trip['Time']
                fee = trip['Fee'] if 'Fee' in trip else get_fee(driver_id)
                slots = trip['Slots'] if 'Slots' in trip else get_slots(driver_id)
                if 'Passengers' in trip:
                    slots -= len(trip['Passengers'])
                    # @PABLO: Maybe it is also useful for passengers to see
                    # the other passengers in their booked trips?
                car = get_car(driver_id)
                bizum = get_bizum(driver_id)

                day_string_list.append(format_trip_from_data(direction,
                                            chat_id=driver_id, time=time,
                                            slots=slots, car=car,
                                            fee=fee, bizum=bizum))
            week_string_list.append('\n\n'.join(day_string_list))
        string = '\n\n'.join(week_string_list)

    return string, trips_dict

def get_user_week_formatted_requests(chat_id):
    """Generates a formatted string with the trip requests for the next
    week ahead from a given user.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.

    Returns
    -------
    (string, dict)
        Formatted string in Telegram's Markdown v2, and the dictionary with
        the week ahead trip requests ordered by date.

    """
    week_strings = week_isoformats()
    weekday_strings = weekdays_from_today()
    reqs_dict = get_requests_by_user(chat_id, week_strings[0], week_strings[-1], True)

    week_string_list = []
    string = ""
    if reqs_dict:
        for date in reqs_dict:
            # Format string with requests
            header = f"*{weekday_strings[week_strings.index(date)]} "\
                     f"{date[8:10]}/{date[5:7]}*"
            sep_length = int(13-len(header)/2)
            day_string_list = [f"{'—'*5} {header} {'—'*sep_length}"]
            for key in reqs_dict[date]:
                req = reqs_dict[date][key]
                direction = req['Direction']
                time = req['Time']
                day_string_list.append(format_request_from_data(direction, time=time))
            week_string_list.append('\n\n'.join(day_string_list))
        string = '\n\n'.join(week_string_list)

    return string, reqs_dict

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
                weekday_string += f"{start_hour}h \- {end_hour}h"
            wd_string_list.append(weekday_string)
        if wd_string_list:
            string = "\n".join(wd_string_list)
        return string

    if not direction:
        dir_string_list = []
        dir_string = ""
        for dir in notif_dict:
            dir_string = f"➡️ Hacia {dir_dict2.get(dir, dir[2:])}:\n"
            dir_string += format_dir(notif_dict[dir])
            dir_string_list.append(dir_string)
        if dir_string_list:
            string = "\n\n".join(dir_string_list)
    else:
        string = format_dir(notif_dict)

    return string

def get_formatted_requests_notif_config(chat_id, direction=None):
    notif_dict = get_request_notification_by_user(chat_id, direction)
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
                weekday_string += f"{start_hour}h \- {end_hour}h"
            wd_string_list.append(weekday_string)
        if wd_string_list:
            string = "\n".join(wd_string_list)
        return string

    if not direction:
        dir_string_list = []
        dir_string = ""
        for dir in notif_dict:
            dir_string = f"➡️ Hacia {dir_dict2.get(dir, dir[2:])}:\n"
            dir_string += format_dir(notif_dict[dir])
            dir_string_list.append(dir_string)
        if dir_string_list:
            string = "\n\n".join(dir_string_list)
    else:
        string = format_dir(notif_dict)

    return string
