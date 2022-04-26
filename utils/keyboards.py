import logging, math
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.database_api import is_driver
from utils.common import weekdays_from_today, week_isoformats, ccd, scd

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
        the time picker keyboard

    Returns
    -------
    InlineKeyboardMarkup
        The keyboard whose callback datas are the trips' IDs.

    """
    n_rows = math.ceil(len(key_list)/4)
    n_cols = math.ceil(len(key_list)/n_rows)
    index = 0
    cbd = 'TRIP_ID'
    keyboard = []
    for i in range(n_rows):
        row = []
        for j in range(n_cols):
            if index==len(key_list):
                continue
            row.append(InlineKeyboardButton(str(index+1),
                                callback_data=ccd(cbd,key_list[index])))
            index += 1
        keyboard.append(row)

    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)
