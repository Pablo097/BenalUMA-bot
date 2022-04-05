import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from data.database_api import is_driver
from utils.common import weekdays_from_today, week_isoformats

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

def weekdays_keyboard():
    """Creates an inline keyboard with the following 7 days of the week.

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
                                        callback_data=week_strings[6])],
                [InlineKeyboardButton("Abortar", callback_data="TRIP_ABORT")]]
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

    hour_string = f"{hour:0>2}"
    minutes_string = f"{minutes:0>2}"
    cbd1 = "TIME_PICKER_"
    cbd2 = f"_{hour_string}_{minutes_string}"

    keyboard = [[InlineKeyboardButton("⬆️", callback_data=f"{cbd1}HOUR_UP{cbd2}"),
                 InlineKeyboardButton("⬆️", callback_data=f"{cbd1}MINUTES_UP{cbd2}")],
                [InlineKeyboardButton(hour_string, callback_data=f"{cbd1}IGNORE{cbd2}"),
                 InlineKeyboardButton(minutes_string, callback_data=f"{cbd1}IGNORE{cbd2}")],
                [InlineKeyboardButton("⬇️", callback_data=f"{cbd1}HOUR_DOWN{cbd2}"),
                 InlineKeyboardButton("⬇️", callback_data=f"{cbd1}MINUTES_DOWN{cbd2}")],
                [InlineKeyboardButton("Confirmar", callback_data=f"{cbd1}SELECTED{cbd2}")]]
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
    data = query.data

    if data.startswith('TIME_PICKER_'):
        data = data[12:]
    else:
        raise SyntaxError('This callback data does not belong to the time picker keyboard.')

    if not data.startswith("IGNORE"):
        time_string = data[-5:]
        data = data[:-6]

        hour, minutes = time_string.split('_')
        hour = int(hour)
        minutes = int(minutes)
        minutes_step = 5

        if data == "SELECTED":
            query.edit_message_reply_markup(None)
            return f"{hour:0>2}:{minutes:0>2}"
        if data == "HOUR_UP":
            hour += 1
        elif data == "HOUR_DOWN":
            hour -= 1
        elif data == "MINUTES_UP":
            minutes += minutes_step
            if minutes>=60:
                hour +=1
        elif data == "MINUTES_DOWN":
            minutes -= minutes_step
            if minutes<0:
                hour -=1

        hour = hour%24
        minutes = minutes%60
        query.edit_message_reply_markup(time_picker_keyboard(hour, minutes, ikbs_list))

    return
