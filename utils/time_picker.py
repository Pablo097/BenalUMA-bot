import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, CallbackContext, CallbackQueryHandler
from utils.common import *

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
    if hour==None or minutes==None:
        current_time = current_time_isoformat(15)
        if hour==None:
            hour = int(current_time[:2])
        if minutes==None:
            minutes = int(current_time[-2:])

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

# Auxiliary function for 'new_trip' and 'see_offers' commands
def process_time_callback(update, context, command, ikbs):
    # Check if update is callback query or new message
    if update.callback_query:
        is_query = True
        query = update.callback_query
    else:
        is_query = False
        command_key = f"{command}_message"

    # Try to obtain time depending on update type
    if is_query:
        query.answer()
        time = time_picker_process(update, context, ikbs)
        if not time:
            return
    else:
        if command_key in context.user_data:
            sent_message = context.user_data.pop(command_key)
            sent_message.edit_reply_markup(None)
        # Obtain time
        try:
            time = obtain_time_from_string(update.message.text)
        except:
            time = None
        if not time:
            text = f"No se ha reconocido una hora válida. Por favor, introduce una "\
                   f"hora en formato HH:MM de 24 horas."
            reply_markup = time_picker_keyboard(ikbs_list=ikbs)
            context.user_data[command_key] = update.message.reply_text(text,
                                                    reply_markup=reply_markup)
            return

    # Check time validity depending on command
    if ((command=='trip' or command=='request') and
            not is_future_datetime(context.user_data[f"{command}_date"], time)):
        if command=='trip':
            text = f"¡No puedes crear un nuevo viaje en el pasado!"
        elif command=='request':
            text = f"¡No puedes pedir un viaje en el pasado!"
        text += f"\nPor favor, introduce una hora válida."
        hour, minutes = time.split(':')
        if not is_query:
            minutes = 0
        reply_markup = time_picker_keyboard(hour, minutes, ikbs)
        if is_query:
            query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            context.user_data[command_key] = update.message.reply_text(text=text,
                                                    reply_markup=reply_markup)
        return

    return time
