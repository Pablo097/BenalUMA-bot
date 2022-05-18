import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (remove_passenger, get_trip_time, get_trip_chat_id)
from messages.format import (get_markdown2_inline_mention,
                          get_formatted_trip_for_driver,
                          get_formatted_trip_for_passenger,
                          get_user_week_formatted_bookings)
from messages.message_queue import send_message
from utils.keyboards import trips_keyboard
from utils.common import *
from utils.decorators import registered, send_typing_action

(MYBOOKINGS_SELECT, MYBOOKINGS_CANCEL, MYBOOKINGS_EXECUTE) = range(40,43)
cdh = 'MB'   # Callback Data Header

# Abort/Cancel buttons
ikbs_end_MB = [[InlineKeyboardButton("Terminar", callback_data=ccd(cdh,"END"))]]
ikbs_back_MB = [[InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK"))]]

logger = logging.getLogger(__name__)

@send_typing_action
@registered
def my_bookings(update, context):
    """Shows all the booked trips for the week ahead"""
    # Check if command was previously called and remove reply markup associated
    if 'MB_message' in context.user_data:
        sent_message = context.user_data.pop('MB_message')
        sent_message.edit_reply_markup(None)
    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('MB_'):
            del context.user_data[key]

    formatted_trips, trips_dict = get_user_week_formatted_bookings(update.effective_chat.id)
    if trips_dict:
        text = f"Viajes reservados para los próximos 7 días:\n\n"
        text += f"{formatted_trips} \n"
        context.user_data['MB_dict'] = trips_dict
        keyboard = [[InlineKeyboardButton("Cancelar reserva", callback_data=ccd(cdh,"CANCEL"))]]
        keyboard += ikbs_end_MB
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['MB_message'] = update.message.reply_text(text,
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return MYBOOKINGS_SELECT
    else:
        text = "No tienes viajes reservados para la próxima semana."
        update.message.reply_text(text)
    return ConversationHandler.END

@send_typing_action
def my_bookings_restart(update, context):
    """Shows all the booked trips for the week ahead"""
    query = update.callback_query
    query.answer()

    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('MB_') and key!='MB_message':
            del context.user_data[key]

    formatted_trips, trips_dict = get_user_week_formatted_bookings(update.effective_chat.id)
    if trips_dict:
        text = f"Viajes reservados para los próximos 7 días:\n\n"
        text += f"{formatted_trips} \n"
        context.user_data['MB_dict'] = trips_dict
        keyboard = [[InlineKeyboardButton("Cancelar reserva", callback_data=ccd(cdh,"CANCEL"))]]
        keyboard += ikbs_end_MB
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return MYBOOKINGS_SELECT
    else:
        text = "No tienes viajes reservados para la próxima semana."
        query.edit_message_text(text)
    return ConversationHandler.END

def choose_booking(update, context):
    """Lets user pick the trip to edit"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the choose_booking function.')

    trips_dict = context.user_data['MB_dict']
    if data[1] == "CANCEL":
        next_state = MYBOOKINGS_CANCEL
        text = f"¿Qué reserva quieres anular?"
        reply_markup = trips_keyboard(trips_dict, cdh, ikbs_back_MB,
                                show_extra_param=False, show_passengers=False)

    query.edit_message_text(text, reply_markup=reply_markup)
    return next_state

def cancel_booking(update, context):
    """Cancels the given booking"""
    query = update.callback_query
    query.answer()

    # Parse trip identifiers
    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='ID'):
        raise SyntaxError('This callback data does not belong to the cancel_booking function.')
    direction = data[2]
    date = data[3]
    trip_key = ';'.join(data[4:])   # Just in case the unique ID constains a ';'
    if direction == 'Ben':
        direction = 'toBenalmadena'
    elif direction == 'UMA':
        direction = 'toUMA'

    # Save trip parameters
    context.user_data['MB_dir'] = direction
    context.user_data['MB_date'] = date
    context.user_data['MB_key'] = trip_key

    # Check if trip hasn't ocurred yet
    time = get_trip_time(direction, date, trip_key)
    if not is_future_datetime(date, time, 15):
        reply_markup = InlineKeyboardMarkup(ikbs_back_MB)
        text = f"🚫 No puedes anular esta reserva porque ya ha pasado\."
    else:
        keyboard = [[InlineKeyboardButton("✔️ Sí, anular", callback_data=ccd(cdh,"CANCEL_CONFIRM")),
                     ikbs_back_MB[0][0]]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"Vas a anular la siguiente reserva:\n\n"
        text += get_formatted_trip_for_passenger(direction, date, trip_key)
        text += f"\n\n¿Estás seguro?"
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return MYBOOKINGS_EXECUTE

def MB_execute_action(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the MB_execute_action function.')

    # Obtain trip parameters
    direction = context.user_data.pop('MB_dir')
    date = context.user_data.pop('MB_date')
    trip_key = context.user_data.pop('MB_key')

    # Check action to execute
    if data[1] == "CANCEL_CONFIRM":
        chat_id = update.effective_chat.id
        remove_passenger(chat_id, direction, date, trip_key)
        text = escape_markdown(f"Tu reserva ha sido anulada correctamente.",2)
        driver_id = get_trip_chat_id(direction, date, trip_key)
        text_driver = f"El usuario {get_markdown2_inline_mention(chat_id)} ha "\
                      f"anulado su reserva en el siguiente viaje:\n\n"
        text_driver += get_formatted_trip_for_driver(direction, date, trip_key)
        send_message(context, driver_id, text_driver, telegram.ParseMode.MARKDOWN_V2,
                        notify_id = chat_id)

    # Remove elements from user's dictionary
    for key in list(context.user_data.keys()):
        if key.startswith('MB_'):
            del context.user_data[key]

    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

def MB_end(update, context):
    """Ends my bookings conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('MB_'):
            del context.user_data[key]
    query.edit_message_reply_markup(None)
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for 'my bookings'
    ny_bookings_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('misreservas', my_bookings)],
        states={
            MYBOOKINGS_SELECT: [
                CallbackQueryHandler(choose_booking, pattern=f"^{ccd(cdh,'CANCEL')}$")
            ],
            MYBOOKINGS_CANCEL: [
                CallbackQueryHandler(cancel_booking, pattern=f"^{ccd(cdh,'ID','.*')}")
            ],
            MYBOOKINGS_EXECUTE: [
                CallbackQueryHandler(MB_execute_action, pattern=f"^{ccd(cdh,'CANCEL_CONFIRM')}$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(my_bookings_restart, pattern=f"^{ccd(cdh,'BACK')}$"),
                   CallbackQueryHandler(MB_end, pattern=f"^{ccd(cdh,'END')}$"),
                   CommandHandler('misreservas', my_bookings)],
    )

    dispatcher.add_handler(ny_bookings_conv_handler)
