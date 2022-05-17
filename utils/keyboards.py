import logging, math
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.database_api import is_driver, get_name
from messages.format import format_trip_from_data
from utils.common import (weekdays, weekdays_en, weekdays_from_today,
                            week_isoformats, ccd, scd)

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
    keyboard = [
        [
            InlineKeyboardButton("Cambiar nombre de usuario", callback_data="CONFIG_NAME"),
        ]
    ]
    if is_driver(chat_id):
        keyboard += [
            [
                InlineKeyboardButton("Asientos libres", callback_data="CONFIG_SLOTS"),
                InlineKeyboardButton("Aceptar Bizum", callback_data="CONFIG_BIZUM"),
            ], [
                InlineKeyboardButton("Descripción vehículo", callback_data="CONFIG_CAR"),
                InlineKeyboardButton("Establecer precio", callback_data="CONFIG_FEE"),
            ]
        ]
    keyboard += [[InlineKeyboardButton("Configuración avanzada", callback_data="CONFIG_ADVANCED")],
                 [InlineKeyboardButton("Terminar", callback_data="CONFIG_END")]]
    return InlineKeyboardMarkup(keyboard)

def weekdays_keyboard(ikbs_list=None):
    """Creates an inline keyboard with the following 7 days of the week.

    Parameters
    ----------
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
                                        callback_data=week_strings[0]),
                 InlineKeyboardButton(f"Mañana ({weekdays_aux[1]} {day_string[1]})",
                                        callback_data=week_strings[1])],
                [InlineKeyboardButton(f"{weekdays_aux[2]} {day_string[2]}",
                                        callback_data=week_strings[2]),
                 InlineKeyboardButton(f"{weekdays_aux[3]} {day_string[3]}",
                                        callback_data=week_strings[3])],
                [InlineKeyboardButton(f"{weekdays_aux[4]} {day_string[4]}",
                                        callback_data=week_strings[4]),
                 InlineKeyboardButton(f"{weekdays_aux[5]} {day_string[5]}",
                                        callback_data=week_strings[5]),
                 InlineKeyboardButton(f"{weekdays_aux[6]} {day_string[6]}",
                                        callback_data=week_strings[6])]]
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

def trips_keyboard(trips_dict, command, ikbs_list=None, show_extra_param=True,
                                                    show_passengers=True):
    """Creates an inline keyboard with formatted trips data which return
    callback datas with format "<command>_ID;<abbr_dir>;<date>;<key>" for each trip button.

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
    cbd = f"{command}_ID"
    keyboard = []
    for date in trips_dict:
        for key in trips_dict[date]:
            trip = trips_dict[date][key]
            direction = trip['Direction']
            time = trip['Time']
            slots = trip['Slots'] if show_extra_param and 'Slots' in trip else None
            fee = trip['Fee'] if show_extra_param and 'Fee' in trip else None
            passengers_list = trip['Passengers'] if show_passengers and 'Passengers' in trip else None
            string = format_trip_from_data(direction, date, time=time,
                                        slots=slots, fee=fee,
                                        passenger_ids=passengers_list,
                                        is_abbreviated=True)
            keyboard.append([InlineKeyboardButton(string,
                        callback_data=ccd(cbd, direction[2:5], date, key))])

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def passengers_keyboard(chat_id_list, ikbs_list=None):
    """Creates an inline keyboard with the passengers' names as buttons,
    returning their respective chat IDs.

    Parameters
    ----------
    chat_id_list : List[int or strings]
        List with the passengers' chat IDs.
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
    cbd = 'PASS_ID'
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
