import logging
import re
from data.database_api import get_name, is_driver, get_slots, get_car, get_fee, get_bizum
from datetime import datetime, date, timedelta
from pytz import timezone

MAX_FEE = 1.5

emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']

def get_formatted_user_config(chat_id):
    """Generates a formatted string with the user configuration.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    string
        Formatted string with user's configuration.

    """
    string = f"💬 *Nombre*: `{get_name(chat_id)}`"
    role = 'Conductor' if is_driver(chat_id) else 'Pasajero'
    string += f"\n🧍 *Rol*: `{role}`"

    if role == 'Conductor':
        string += f"\n💺 *Asientos disponibles*: `{str(get_slots(chat_id))}`"
        string += f"\n🚘 *Descripción vehículo*: `{get_car(chat_id)}`"
        fee = get_fee(chat_id)
        if fee != None:
            string += f"\n🪙 *Pago por trayecto*: `{str(fee).replace('.',',')}€`"
        bizum = get_bizum(chat_id)
        if bizum == True:
            string += f"\n💸 `Aceptas Bizum`"
        elif bizum == False:
            string += f"\n💸🚫 `NO aceptas Bizum`"

    return string

def obtain_float_from_string(text):
    """Obtains a float from a given string. Used to extract the price.

    Parameters
    ----------
    text : string
        String where the float is contained.

    Returns
    -------
    float
        The number obtained from the string, if any.

    """
    regex_pattern = "([0-9]*[.,'])?[0-9]+"
    number = float(re.search(regex_pattern, text).group().replace(',','.').replace("'",'.'))
    return number

def dates_from_today(number_of_days):
    """Obtains a list of dates from today.

    Parameters
    ----------
    number_of_days : int
        The number of days from today to include in the list.

    Returns
    -------
    List[date]
        Date objects with the days from today.

    """
    madrid = timezone('Europe/Madrid')
    today = datetime.now(madrid).date()
    delta = timedelta(days=1)
    dates = []
    for n in range(number_of_days):
        dates.append(today+n*delta)
    return dates

def today_isoformat():
    """Generates the ISO-formatted string of today's date.

    Returns
    -------
    string
        Today's date as 'YYYY-mm-dd'.

    """
    return dates_from_today(1)[0].isoformat()

def week_isoformats():
    """Obtains a list of the ISO-formatted strings of a whole week from today.

    Returns
    -------
    list[string]
        List with strings as 'YYYY-mm-dd'.

    """
    return [date.isoformat() for date in dates_from_today(7)]

def weekdays_from_today():
    """Obtains a list of the weekdays of a whole week from today.

    Returns
    -------
    list[string]
        List with strings as ['Thursday', 'Friday', ... , 'Wednesday'] if today
        is Thursday.

    """
    return [weekdays[date.weekday()] for date in dates_from_today(7)]

def is_future_datetime(date, time):
    """Checks whether the input datetime is in the future from now.

    Parameters
    ----------
    date : string
        Date with ISO format 'YYYY-mm-dd'
    time : string
        Time with ISO format 'HH:MM'

    Returns
    -------
    Boolean
        True if input datetime is future, false if it is past from now.

    """
    madrid = timezone('Europe/Madrid')
    now = datetime.now(madrid).replace(tzinfo=None)
    input_datetime = datetime.fromisoformat(f"{date}T{time}")
    return input_datetime > now
