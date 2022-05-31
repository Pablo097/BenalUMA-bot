import logging
import re
from datetime import datetime, date, timedelta, time
from pytz import timezone

MAX_FEE = 1.5

# Dictionaries for generalizing the code and making it prettier
dir_dict = {'toUMA': 'UMA', 'toBenalmadena':'Benalmádena'}
dir_dict2 = dict(dir_dict.items())
dir_dict2[list(dir_dict.keys())[0]] = 'la '+dir_dict2[list(dir_dict.keys())[0]]
abbr_dir_dict = {key[2:5].upper():key for (key,value) in dir_dict.items()}

emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
weekdays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
weekdays_en = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
madrid = timezone('Europe/Madrid')

## Parsing

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

def obtain_time_from_string(text):
    """Obtains 24-hour time from a given string.

    Parameters
    ----------
    text : type
        String where the time is contained.

    Returns
    -------
    string
        Description of returned object.

    """

    regex_pattern = "(2[0-3]|[01]?[0-9])([:.,']([0-9]{2}))?"
    time = re.search(regex_pattern, text).group()
    time = re.split("[.,:']", time)
    time_string = f"{time[0]:0>2}:"
    if len(time) < 2:
        time_string += "00"
    elif float(time[1]) > 59:
        raise ValueError('Minutes cannot be greater than 59.')
    else:
        time_string += f"{time[1]:0>2}"
    return time_string

# Callback data handling

def ccd(*args):
    """ CCD: Create Callback Data.
    Creates a string of the passed arguments separated by semicolons"""
    return ";".join(str(i) for i in args)

def scd(data):
    """ SCD: Separate Callback Data.
    Returns a list of the separated data created with 'create_callback_data'"""
    return [i for i in data.split(";")]

## Dates handling

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

def get_weekday_from_date(date):
    """Returns a string with the weekday of the given date.

    Parameters
    ----------
    date : string
        Date with ISO format 'YYYY-mm-dd'

    Returns
    -------
    str
        Weekday of the date.

    """
    return weekdays[datetime.fromisoformat(date).weekday()]

def current_time_isoformat(minutes_divisor=None):
    """Returns the string representation of the current time.

    Parameters
    ----------
    minutes_divisor : int
        The required divisor of the minutes to return.
        For example, if minutes_divisor=15, then the returned minutes
        could only be (0, 15, 30, 45).

    Returns
    -------
    string
        ISO format of current time as HH:MM.

    """
    time1 = datetime.now(madrid).time()
    if minutes_divisor:
        minutes = time1.minute
        time1 = time1.replace(minute=(minutes-minutes%minutes_divisor))
    text = time1.isoformat('minutes')
    return text

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

def is_future_datetime(date, time, minutes_margin=0):
    """Checks whether the input datetime is in the future from now.

    Parameters
    ----------
    date : string
        Date with ISO format 'YYYY-mm-dd'
    time : string
        Time with ISO format 'HH:MM'
    minutes_margin : int
        This number of minutes will be added to the inputted datetime before
        comparing it to now.

    Returns
    -------
    Boolean
        True if input datetime is future, false if it is past from now.

    """
    now = datetime.now(madrid).replace(tzinfo=None)
    input_datetime = datetime.fromisoformat(f"{date}T{time}")
    return input_datetime+timedelta(minutes=minutes_margin) > now

def is_greater_isotime(time1, time2):
    return time.fromisoformat(time1) > time.fromisoformat(time2)

def get_time_range_from_center_time(central_time, hour_delta, minutes_delta=0):
    """Returns the initial and end times from a central time, adding and
    substracting the time delta from it.

    Parameters
    ----------
    central_time : string
        Central time for the time range, with ISO format 'HH:MM'.
    hour_delta : int
        Hours to add and substract to the central time.
    minutes_delta : int
        Minutes to add and substract to the central time.

    Returns
    -------
    (string, string)
        Start and end times in ISO format 'HH:MM'

    """
    ctime = time.fromisoformat(central_time)
    dtime = timedelta(hours=hour_delta, minutes=minutes_delta)

    time_start = (datetime.combine(date.today(), ctime) - dtime).time()
    if time_start>ctime:
        time_start = time()

    time_end = (datetime.combine(date.today(), ctime) + dtime).time()
    if time_end<ctime:
        time_end = time(hour=23,minute=59)

    # hour = int(time[:2])
    # time_before = f"{(hour-1):02}:{time[-2:]}" if hour>0 else "00:00"
    # time_after = f"{(hour+1):02}:{time[-2:]}" if hour<23 else "23:59"

    return (time_start.isoformat('minutes'), time_end.isoformat('minutes'))
