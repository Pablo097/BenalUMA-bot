import logging, math
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.database_api import is_driver, get_name
from messages.format import format_trip_from_data, format_request_from_data
from utils.common import *

def config_keyboard(chat_id):
    """Creates an inline keyboard with the user configuration options.

    Parameters
    ----------
    chat_id : int
        User's chat id.

    Returns
    -------
    InlineKeyboardMarkup

    """
    cdh = 'CONFIG'
    keyboard = [
        [
            InlineKeyboardButton("Cambiar nombre de usuario", callback_data=ccd(cdh,"NAME")),
        ]
    ]
    if is_driver(chat_id):
        univ, home = list(dir_dict.values())
        keyboard += [
            [
                InlineKeyboardButton("Asientos libres", callback_data=ccd(cdh,"SLOTS")),
                InlineKeyboardButton("Aceptar Bizum", callback_data=ccd(cdh,"BIZUM")),
            ], [
                InlineKeyboardButton("Descripción vehículo", callback_data=ccd(cdh,"CAR")),
                InlineKeyboardButton("Establecer precio", callback_data=ccd(cdh,"FEE")),
            ], [
                InlineKeyboardButton(f"Zona {home}", callback_data=ccd(cdh,"HOME")),
                InlineKeyboardButton(f"Zona {univ}", callback_data=ccd(cdh,"UNIV")),
            ]
        ]
    keyboard += [[InlineKeyboardButton("Configuración avanzada", callback_data=ccd(cdh,"ADVANCED"))],
                 [InlineKeyboardButton("Terminar", callback_data=ccd(cdh,"END"))]]
    return InlineKeyboardMarkup(keyboard)

def seats_keyboard(max_seats, cdh, min_seats=1, ikbs_list=None):
    """Creates an inline keyboard with numbered buttons that return the number
    of seats

    Parameters
    ----------
    max_seats : int
        Maximum number of seats to display
    cdh : string
        Callback Data Header: Word to add at the beginning of each of the
        callback datas for better identification.
    min_seats : int
        Minimum number of seats to display
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the inline keyboard.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas are the numbers.

    """
    num_seats = max_seats-min_seats+1
    n_rows = math.ceil(num_seats/3)
    n_cols = math.ceil(num_seats/n_rows)
    index = min_seats
    keyboard = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            # If no more items, dont try to append more to row
            if index>max_seats:
                continue
            row.append(InlineKeyboardButton(emoji_numbers[index],
                                            callback_data=ccd(cdh,str(index))))
            index += 1
        keyboard.append(row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def weekdays_keyboard(cdh, ikbs_list=None):
    """Creates an inline keyboard with the following 7 days of the week.

    Parameters
    ----------
    cdh : string
        Callback Data Header: Word to add at the beginning of each of the
        callback datas for better identification.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the keyboard

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas are the ISO representation of the
        selected date.

    """
    weekdays_aux = weekdays_from_today()
    week_strings = week_isoformats()
    day_string = [weekdate.split('-')[-1].lstrip('0')for weekdate in week_strings]
    keyboard = [[InlineKeyboardButton(f"Hoy ({weekdays_aux[0]} {day_string[0]})",
                                        callback_data=ccd(cdh,week_strings[0])),
                 InlineKeyboardButton(f"Mañana ({weekdays_aux[1]} {day_string[1]})",
                                        callback_data=ccd(cdh,week_strings[1]))],
                [InlineKeyboardButton(f"{weekdays_aux[2]} {day_string[2]}",
                                        callback_data=ccd(cdh,week_strings[2])),
                 InlineKeyboardButton(f"{weekdays_aux[3]} {day_string[3]}",
                                        callback_data=ccd(cdh,week_strings[3]))],
                [InlineKeyboardButton(f"{weekdays_aux[4]} {day_string[4]}",
                                        callback_data=ccd(cdh,week_strings[4])),
                 InlineKeyboardButton(f"{weekdays_aux[5]} {day_string[5]}",
                                        callback_data=ccd(cdh,week_strings[5])),
                 InlineKeyboardButton(f"{weekdays_aux[6]} {day_string[6]}",
                                        callback_data=ccd(cdh,week_strings[6]))]]
    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def trip_ids_keyboard(key_list, ikbs_list=None):
    """Creates an inline keyboard with numbered buttons that return the trip IDs.

    Parameters
    ----------
    key_list : List[strings]
        List with the strings of the trips' IDs.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the inline keyboard.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas are the trips' IDs.

    """
    n_trips = len(key_list)
    n_rows = math.ceil(n_trips/4)
    n_cols = math.ceil(n_trips/n_rows)
    index = 0
    cbd = 'TRIP_ID'
    keyboard = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            # If no more items, dont try to append more to row
            if index==n_trips:
                continue
            row.append(InlineKeyboardButton(str(index+1),
                                callback_data=ccd(cbd,key_list[index])))
            index += 1
        keyboard.append(row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def requests_ids_keyboard(key_list, ikbs_list=None):
    """Creates an inline keyboard with numbered buttons that return the request
    IDs.

    Parameters
    ----------
    key_list : List[strings]
        List with the strings of the requests' IDs.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the inline keyboard.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas are the requests' IDs.

    """
    n_reqs = len(key_list)
    n_rows = math.ceil(n_reqs/4)
    n_cols = math.ceil(n_reqs/n_rows)
    index = 0
    cbd = 'REQ_ID'
    keyboard = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            # If no more items, dont try to append more to row
            if index==n_reqs:
                continue
            row.append(InlineKeyboardButton(str(index+1),
                                callback_data=ccd(cbd,key_list[index])))
            index += 1
        keyboard.append(row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def trips_keyboard(trips_dict, command, ikbs_list=None, show_extra_param=True,
                                                    show_passengers=True):
    """Creates an inline keyboard with formatted trips data which return
    callback datas with format "<command>;ID;<abbr_dir>;<date>;<key>" for each trip button.

    Parameters
    ----------
    trips_dict : dict
        Dictionary with the ordered-by-date trips data.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the inline keyboard.
    show_extra_param : boolean
        Flag that indicates if 'fee' and 'slots' parameters need to be shown.
    show_passengers : boolean
        Flag that indicates if passengers need to be shown.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas have the explained format.

    """
    cbd = ccd(command,'ID')
    keyboard = []
    for date in trips_dict:
        for key in trips_dict[date]:
            trip = trips_dict[date][key]
            direction = trip['Direction']
            time = trip['Time']
            slots = trip['Slots'] if show_extra_param and 'Slots' in trip else None
            fee = trip['Fee'] if show_extra_param and 'Fee' in trip else None
            origin = trip['Origin'] if show_extra_param and 'Origin' in trip else None
            dest = trip['Dest'] if show_extra_param and 'Dest' in trip else None
            passengers_list = trip['Passengers'] if show_passengers and 'Passengers' in trip else None
            string = format_trip_from_data(direction, date, time=time,
                                        slots=slots, fee=fee,
                                        passenger_ids=passengers_list,
                                        origin=origin, dest=dest,
                                        is_abbreviated=True)
            keyboard.append([InlineKeyboardButton(string,
                        callback_data=ccd(cbd, direction[2:5].upper(), date, key))])

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def requests_keyboard(reqs_dict, command, ikbs_list=None):
    """Creates an inline keyboard with formatted requests data which return
    callback datas with format "<command>;ID;<abbr_dir>;<date>;<key>" for each
    request button.

    Parameters
    ----------
    reqs_dict : dict
        Dictionary with the ordered-by-date trip requests data.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the inline keyboard.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas have the explained format.

    """
    cbd = ccd(command,'ID')
    keyboard = []
    for date in reqs_dict:
        for key in reqs_dict[date]:
            req = reqs_dict[date][key]
            direction = req['Direction']
            time = req['Time']
            string = format_request_from_data(direction, date, time=time,
                                                    is_abbreviated=True)
            keyboard.append([InlineKeyboardButton(string,
                        callback_data=ccd(cbd, direction[2:5].upper(), date, key))])

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def passengers_keyboard(chat_id_list, cdh, ikbs_list=None):
    """Creates an inline keyboard with the passengers' names as buttons,
    returning their respective chat IDs.

    Parameters
    ----------
    chat_id_list : List[int or strings]
        List with the passengers' chat IDs.
    cdh : string
        Callback Data Header: Word to add at the beginning of each of the
        callback datas for better identification.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the inline keyboard.

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas are the passengers' IDs.

    """
    n_passengers = len(chat_id_list)
    n_cols = 2
    n_rows = math.ceil(n_passengers/n_cols)
    index = 0
    cbd = ccd(cdh,'PASS_ID')
    keyboard = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            # If no more items, dont try to append more to row
            if index==n_passengers:
                continue
            row.append(InlineKeyboardButton(get_name(chat_id_list[index]),
                                callback_data=ccd(cbd,chat_id_list[index])))
            index += 1
        keyboard.append(row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def notif_weekday_keyboard(cdh, opt, ikbs_list=None):
    weekdays_aux = ["TODOS"]+weekdays
    weekdays_en_aux = ["ALL"]+[wd[:3].upper() for wd in weekdays_en]

    keyboard = []
    row = []

    for i in range(len(weekdays_aux)):
        if i!=0 and i%3==0:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(weekdays_aux[i],
                    callback_data=ccd(cdh,opt,weekdays_en_aux[i])))
    keyboard.append(row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def notif_time_keyboard(cdh, opt, first_hour=0, last_hour=24, ikbs_list=None):
    keyboard = []
    row = []

    for i in range(last_hour, first_hour-1, -1):
        if i!=last_hour and (last_hour-i)%6==0:
            keyboard.insert(0, row)
            row = []
        row.insert(0, InlineKeyboardButton(str(i),
                    callback_data=ccd(cdh,opt,str(i))))
    keyboard.insert(0, row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)
