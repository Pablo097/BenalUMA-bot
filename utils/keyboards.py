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

def time_picker_keyboard(hour=None, minutes=None, ikbs_list=None):
    """Creates an inline keyboard with a time picker.

    Parameters
    ----------
    hour : int
        Hour to display in the keyboard.
    minutes : int
        Minutes to display in the keyboard.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the time picker keyboard

    Returns
    -------
    InlineKeyboardMarkup

    """
    if hour==None:
        hour = 12
    if minutes==None:
        minutes = 0

    cbd = "TIME_PICKER"
    hs = f"{hour:0>2}"
    ms = f"{minutes:0>2}"

    keyboard = [
        [InlineKeyboardButton("⬆️", callback_data=ccd(cbd,'HOUR_UP',hs,ms)),
         InlineKeyboardButton("⬆️", callback_data=ccd(cbd,'MINUTES_UP',hs,ms))],
        [InlineKeyboardButton(hs, callback_data=ccd(cbd,'IGNORE',hs,ms)),
         InlineKeyboardButton(ms, callback_data=ccd(cbd,'IGNORE',hs,ms))],
        [InlineKeyboardButton("⬇️", callback_data=ccd(cbd,'HOUR_DOWN',hs,ms)),
         InlineKeyboardButton("⬇️", callback_data=ccd(cbd,'MINUTES_DOWN',hs,ms))],
        [InlineKeyboardButton("Confirmar", callback_data=ccd(cbd,'SELECTED',hs,ms))]]
    if ikbs_list:
        keyboard += ikbs_list
    return InlineKeyboardMarkup(keyboard)

def time_picker_process(update, context, ikbs_list=None):
    """Short summary.

    Parameters
    ----------
    update : telegram.Update
        The update as provided by the CallbackQueryHandler.
    context : telegram.ext.CallbackContext
        The context as provided by the CallbackQueryHandler.
    ikbs_list : List[List[telegram.InlineKeyboardButton]]
        If not None, the buttons in this list will be added at the bottom of
        the time picker keyboard, if necessary.

    Returns
    -------
    string
        Time in ISO format (HH:MM), if the time is selected. Otherwise, None.

    """
    query = update.callback_query
    data = scd(query.data)

    if data[0] != 'TIME_PICKER':
        raise SyntaxError('This callback data does not belong to the time picker keyboard.')

    command = data[1]
    if command != "IGNORE":
        hour, minutes = data[2:4]
        hour = int(hour)
        minutes = int(minutes)
        minutes_step = 5

        if command == "SELECTED":
            query.edit_message_reply_markup(None)
            return f"{hour:0>2}:{minutes:0>2}"
        if command == "HOUR_UP":
            hour += 1
        elif command == "HOUR_DOWN":
            hour -= 1
        elif command == "MINUTES_UP":
            minutes += minutes_step
            if minutes>=60:
                hour +=1
        elif command == "MINUTES_DOWN":
            minutes -= minutes_step
            if minutes<0:
                hour -=1

        hour = hour%24
        minutes = minutes%60
        query.edit_message_reply_markup(time_picker_keyboard(hour, minutes, ikbs_list))

    return

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
