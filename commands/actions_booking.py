import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (get_name, get_slots, get_trip, get_trip_chat_id,
                                get_number_of_passengers, get_trip_slots,
                                add_passenger, is_passenger, get_trip_time,
                                get_requests_by_user_and_date, delete_request)
from messages.format import (get_markdown2_inline_mention,
                          get_formatted_trip_for_passenger,
                          get_formatted_trip_for_driver,
                          get_formatted_offered_trips,
                          format_request_from_data)
from messages.message_queue import send_message
from utils.keyboards import (weekdays_keyboard, trip_ids_keyboard)
from utils.time_picker import (time_picker_keyboard, process_time_callback)
from utils.common import *
from utils.decorators import registered, send_typing_action

# 'See Offers' conversation points
(SO_START, SO_DATE, SO_HOUR, SO_HOUR_SELECT_RANGE_START,
            SO_HOUR_SELECT_RANGE_STOP, SO_VISUALIZE, SO_REVIEW) = range(10,17)
cdh = 'SO'   # Callback Data Header

# Abort/Cancel buttons
ikbs_cancel_SO = [[InlineKeyboardButton("Cancelar", callback_data=ccd(cdh,"CANCEL"))]]

logger = logging.getLogger(__name__)

@registered
def see_offers(update, context):
    """Asks for requisites of the trips to show"""
    # Check if command was previously called and remove reply markup associated
    if 'SO_message' in context.user_data:
        sent_message = context.user_data.pop('SO_message')
        sent_message.edit_reply_markup(None)

    opt = 'DIR'
    row = []
    for dir in dir_dict2:
        row.append(InlineKeyboardButton(f"Hacia {dir_dict2[dir]}",
                                    callback_data=ccd(cdh,opt,dir[2:5].upper())))
    keyboard = [row] + ikbs_cancel_SO
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Indica la dirección de los viajes ofertados que quieres ver:"
    context.user_data['SO_message'] = update.message.reply_text(text,
                                                reply_markup=reply_markup)
    return SO_START

def SO_select_date(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='DIR'):
        raise SyntaxError('This callback data does not belong to the SO_select_date function.')

    if data[2] in abbr_dir_dict:
        context.user_data['SO_dir'] = abbr_dir_dict[data[2]]
    else:
        logger.warning("Error in SO direction argument.")
        text = f"Error en opción recibida. Abortando..."
        query.edit_message_text(text=text, reply_markup=None)
        return ConversationHandler.END

    reply_markup = weekdays_keyboard(cdh, ikbs_cancel_SO)
    text = f"De acuerdo. ¿Para qué día quieres ver los viajes ofertados?"
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SO_DATE

def SO_select_hour(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the SO_select_hour function.')

    context.user_data['SO_date'] = data[1]
    text = f"Por último, ¿quieres ver todos los viajes ofertados para este día,"\
           f" o prefieres indicar el rango horario en el que estás interesado?"

    keyboard = [[InlineKeyboardButton("Ver todos", callback_data=ccd(cdh,'ALL')),
                 InlineKeyboardButton("Indicar rango horario", callback_data=ccd(cdh,'RANGE'))]]
    keyboard += ikbs_cancel_SO
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SO_HOUR

def SO_select_hour_range_start(update, context):
    query = update.callback_query
    query.answer()

    text = f"De acuerdo. Primero indica la hora de comienzo para buscar viajes ofertados:"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_cancel_SO)
    query.edit_message_text(text=text, reply_markup=reply_markup)
    return SO_HOUR_SELECT_RANGE_START

def SO_select_hour_range_stop(update, context):
    time = process_time_callback(update, context, 'SO', ikbs_cancel_SO)
    if not time:
        return SO_HOUR_SELECT_RANGE_START
    else:
        context.user_data['SO_time_start'] = time
        text = f"Ahora indica hasta qué hora buscar viajes."\
               f"\n(También puedes mandarme un mensaje con la hora directamente)"
        reply_markup = time_picker_keyboard(ikbs_list=ikbs_cancel_SO)
        if update.callback_query:
            update.callback_query.edit_message_text(text=text, reply_markup=reply_markup)
        else:
            context.user_data['SO_message'] = update.message.reply_text(text=text,
                                                    reply_markup=reply_markup)
    return SO_HOUR_SELECT_RANGE_STOP

@send_typing_action
def SO_visualize(update, context):
    # Check type of callback
    if update.callback_query:
        is_query = True
        query = update.callback_query
    else:
        is_query = False

    time_start = None
    time_stop = None

    # If we come from SO_review function, trip requisites are already stored
    if (is_query and scd(query.data)[0]==cdh and scd(query.data)[1]=='CANCEL'):
        time_start = context.user_data.get('SO_time_start')
        time_stop = context.user_data.get('SO_time_stop')
    # Check whether we expect an stop time
    elif 'SO_time_start' in context.user_data:
        time = process_time_callback(update, context, 'SO', ikbs_cancel_SO)
        if not time:
            return SO_HOUR_SELECT_RANGE_STOP
        else:
            # Check if stop time is greater than start one
            if is_greater_isotime(context.user_data['SO_time_start'], time):
                text = f"¡La hora final del rango debe ser mayor a la inicial!"\
                       f"\nPor favor, introduce una hora válida (mayor que"\
                       f" {context.user_data['SO_time_start']})."
                hour, minutes = time.split(':')
                if not is_query:
                    minutes = 0
                reply_markup = time_picker_keyboard(hour, minutes, ikbs_cancel_SO)
                if is_query:
                    query.edit_message_text(text=text, reply_markup=reply_markup)
                else:
                    context.user_data['SO_message'] = update.message.reply_text(text=text,
                                                            reply_markup=reply_markup)
                return SO_HOUR_SELECT_RANGE_STOP
            else:
                time_start = context.user_data['SO_time_start']
                time_stop = time
                context.user_data['SO_time_stop'] = time

    dir = context.user_data['SO_dir']
    date = context.user_data['SO_date']

    text = f"Viajes ofertados hacia *{dir_dict2[dir]}*"\
           f" el {get_weekday_from_date(date)} día *{date[8:10]}/{date[5:7]}*"
    if time_start:
        text += f" entre las *{time_start}* y las *{time_stop}*"
    text += f":\n\n"
    text_aux, key_list = get_formatted_offered_trips(dir, date, time_start, time_stop)
    if text_aux:
        text += text_aux
        if dir==list(dir_dict.keys())[0]:
            text += f"\n\nRecuerda que, en sentido {list(dir_dict.values())[1]}"\
                    f"→{dir_dict[dir]}, se indica la hora de llegada estimada\."
        elif dir==list(dir_dict.keys())[1]:
            text += f"\n\nRecuerda que, en sentido {list(dir_dict.values())[0]}"\
                    f"→{dir_dict[dir]}, se indica la hora de salida\."
        text += f"\n\nSi quieres reservar plaza en alguno de estos viajes, pulsa el"\
                f" botón correspondiente a la opción deseada:"
        reply_markup = trip_ids_keyboard(key_list, ikbs_cancel_SO)
        next_state = SO_VISUALIZE
    else:
        text += "No existen viajes ofertados en las fechas seleccionadas\."
        reply_markup = None
        for key in list(context.user_data.keys()):
            if key.startswith('SO_'):
                del context.user_data[key]
        next_state = ConversationHandler.END

    if is_query:
        query.edit_message_text(text=text, reply_markup=reply_markup,
                                    parse_mode=telegram.ParseMode.MARKDOWN_V2)
    else:
        context.user_data['SO_message'] = update.message.reply_text(text=text,
                                            reply_markup=reply_markup,
                                            parse_mode=telegram.ParseMode.MARKDOWN_V2)

    if next_state==ConversationHandler.END and 'SO_message' in context.user_data:
        del context.user_data['SO_message']

    return next_state

def SO_review(update, context):
    query = update.callback_query
    query.answer()

    dir = context.user_data['SO_dir']
    date = context.user_data['SO_date']
    data = scd(query.data)
    if data[0] != 'TRIP_ID':
        raise SyntaxError('This callback data does not belong to the SO_review function.')

    trip_key = ';'.join(data[1:])   # Just in case the unique ID constains a ';'
    context.user_data['SO_key'] = trip_key

    ok = False
    user_id = update.effective_chat.id
    time = get_trip_time(dir, date, trip_key)
    if time == None:
        text = escape_markdown(f"⚠️ Este viaje ya no existe.",2)
    # Check that user is not the driver
    elif user_id == get_trip_chat_id(dir, date, trip_key):
        text = f"🚫 No puedes reservar este viaje... ¡Eres tú quien lo conduce! 😠"
        text = escape_markdown(text,2)
    # Check that user is not already passenger
    elif is_passenger(user_id, dir, date, trip_key):
        text = f"🚫 No puedes volver a reservar este viaje. Ya eres un pasajero confirmado."
        text = escape_markdown(text,2)
    # Check if trip hasn't ocurred yet
    elif not is_future_datetime(date, time):
        text = f"🚫 No puedes reservar este viaje porque la hora de salida ya"\
               f" ha pasado. Puedes preguntarle personalmente al conductor por"\
               f" mensaje privado pulsando sobre su nombre.\n\n"
        text = escape_markdown(text, 2)
        text += get_formatted_trip_for_passenger(dir, date, trip_key)
    # Everything is ok
    else:
        ok = True

    if ok:
        text = f"Vas a enviar una solicitud de reserva para el siguiente viaje:\n\n"
        text += get_formatted_trip_for_passenger(dir, date, trip_key)
        text += f"\n\n¿Estás seguro?"
        keyboard = [[InlineKeyboardButton("✅ Sí, enviar",
                                            callback_data=ccd(cdh,'CONFIRM_RSV')),
                     ikbs_cancel_SO[0][0]]]
        query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard),
                                parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return SO_REVIEW
    else:
        query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        for key in list(context.user_data.keys()):
            if key.startswith('SO_'):
                del context.user_data[key]
        return ConversationHandler.END

def SO_reserve(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='CONFIRM_RSV'):
        raise SyntaxError('This callback data does not belong to the SO_reserve function.')

    dir = context.user_data.pop('SO_dir')
    date = context.user_data.pop('SO_date')
    trip_key = context.user_data.pop('SO_key')
    user_id = update.effective_chat.id
    driver_id = get_trip_chat_id(dir, date, trip_key)
    if driver_id == None:
        text = escape_markdown(f"⚠️ Este viaje ya no existe.",2)
        query.edit_message_text(text=text)
        return ConversationHandler.END

    # Send petition to driver
    text_driver = f"🛎️ Tienes una nueva petición de reserva de "\
                  f"{get_markdown2_inline_mention(user_id)} para el siguiente viaje:\n\n"
    text_driver += get_formatted_trip_for_driver(dir, date, trip_key)

    cbd = 'ALERT'
    driver_keyboard = [[InlineKeyboardButton("✅ Aceptar",
                callback_data=ccd(cbd, 'Y', user_id, dir[2:5].upper(), date, trip_key)),
                        InlineKeyboardButton("❌ Rechazar",
                callback_data=ccd(cbd, 'N', user_id, dir[2:5].upper(), date, trip_key))]]
    try:
        context.bot.send_message(driver_id, text_driver,
                                reply_markup=InlineKeyboardMarkup(driver_keyboard),
                                parse_mode=telegram.ParseMode.MARKDOWN_V2)
        text = f"¡Hecho! Se ha enviado una petición de reserva para este viaje. 📨\n\n"
        text = escape_markdown(text, 2)
        text += get_formatted_trip_for_passenger(dir, date, trip_key)
        text_aux = f"\n\nAhora tienes que esperar a que el conductor decida si"\
                   f" confirmar o rechazar tu solicitud. Te volveré a avisar"\
                   f" en cualquier caso, no te preocupes.\nRecuerda que siempre"\
                   f" puedes contactar con el conductor pulsando sobre su nombre"\
                   f" si lo necesitas."
        text += escape_markdown(text_aux, 2)
    except:
        logger.warning(f"Booking reservation alert couldn't be sent to driver with chat_id:{driver_id}.")
        text = f"🚫 No se ha podido enviar la petición de reserva al conductor,"\
               f" quizás porque haya bloqueado al bot. 🚫\nPor favor, mándale un"\
               f" mensaje privado pulsando en su nombre si sigues interesado.\n\n"
        text = escape_markdown(text, 2)
        text += get_formatted_trip_for_passenger(dir, date, trip_key)

    query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    for key in list(context.user_data.keys()):
        if key.startswith('SO_'):
            del context.user_data[key]
    return ConversationHandler.END

def SO_cancel(update, context):
    """Cancels see offers conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('SO_'):
            del context.user_data[key]
    query.edit_message_text(text="Se ha cancelado la visualización de viajes ofertados.")
    return ConversationHandler.END

def SO_end(update, context):
    """End the conversation when offers have already been shown"""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('SO_'):
            del context.user_data[key]
    # query.edit_message_text(text="Ok, no se ha pedido ninguna reserva.")
    text = query.message.text
    query.edit_message_text(text[:text.rfind('\n')], entities=query.message.entities)
    return ConversationHandler.END

def alert_user(update, context):
    query = update.callback_query
    query.answer()

    driver_id = update.effective_chat.id
    data = scd(query.data)
    if data[0] != 'ALERT':
        raise SyntaxError('This callback data does not belong to the alert_user function.')

    action, user_id, dir, date = data[1:5]
    trip_key = ';'.join(data[5:])   # Just in case the unique ID constains a ';'
    dir = abbr_dir_dict[dir]

    reservation_ok = False
    # Check that trip still exists
    time = get_trip_time(dir, date, trip_key)
    if time == None:
        text = escape_markdown(f"⚠️ Este viaje ya no existe.",2)
        text_booker = ""
    # Check action
    elif action == "Y":
        if is_passenger(user_id, dir, date, trip_key):
            text = f"⚠️ No puedes aceptar a este usuario porque ya es un"\
                   f" pasajero confirmado para este viaje."
            text = escape_markdown(text,2)
            text_booker = ""
        else:
            slots = get_trip_slots(dir, date, trip_key)
            if slots==None:
                slots = get_slots(driver_id)
            slots -= get_number_of_passengers(dir, date, trip_key)

            if slots > 0: # If trip is not full, it accepts the passenger
                add_passenger(user_id, dir, date, trip_key)
                text = escape_markdown("¡Hecho! Tienes una nueva plaza reservada.\n\n",2)
                text += get_formatted_trip_for_driver(dir, date, trip_key)
                text_booker = f"¡Enhorabuena! Te han confirmado la reserva para "\
                              f"el siguiente viaje.\n\n"
                reservation_ok = True
            else:
                text = f"⚠️ Atención, no te quedan plazas para este viaje. No es "\
                       f"posible confirmar esta reserva."
                text = escape_markdown(text,2)
                text_booker = f"⚠️ Atención, no se ha podido confirmar la reserva "\
                              f"porque no quedan más plazas libres. Contacta con el "\
                              f"conductor pulsando sobre su nombre si quieres "\
                              f"preguntarle sobre la disponibilidad.\n\n"
    elif action == "N":
        text = escape_markdown("🚫 Has rechazado la petición de reserva.",2)
        text_booker = f"❌ Tu petición de reserva para el siguiente viaje ha"\
                      f" sido rechazada.\n\n"

    # Send messages
    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    if text_booker:
        text_booker = escape_markdown(text_booker,2)
        text_booker += get_formatted_trip_for_passenger(dir, date, trip_key,
                                        is_abbreviated = not reservation_ok)
        send_message(context, user_id, text_booker, telegram.ParseMode.MARKDOWN_V2,
                            notify_id = driver_id)
        if reservation_ok:
            # Check if passenger had any trip requests near this trip,
            # delete it and notify the deletion to passenger
            time_start, time_end = get_time_range_from_center_time(time, 1)
            req_dict = get_requests_by_user_and_date(user_id, dir, date,
                                                    time_start, time_end)
            if req_dict:
                for key in req_dict:
                    delete_request(dir, date, key)
                    text_booker2 = f"Al haber reservado el viaje, se ha eliminado"\
                                   f" tu siguiente petición con requisitos"\
                                   f" similares:\n\n"
                    text_booker2 += format_request_from_data(dir, date,
                                                    time=req_dict[key]['Time'])
                    send_message(context, user_id, text_booker2,
                                            telegram.ParseMode.MARKDOWN_V2)

def reserve_from_notification(update, context):
    """Gateway to SO_review when booking from a new trip notification"""
    query = update.callback_query
    data = scd(query.data)
    if data[0] != 'RSV':
        raise SyntaxError('This callback data does not belong to the reserve_from_notification function.')

    if data[1]=='DISMISS':
        query.answer()
        # query.edit_message_reply_markup()
        text = query.message.text
        query.edit_message_text(text[:text.rfind('.')+1], entities=query.message.entities)
        return ConversationHandler.END

    dir, date = data[1:3]
    trip_key = ';'.join(data[3:])   # Just in case the unique ID constains a ';'

    context.user_data['SO_dir'] = abbr_dir_dict[dir]
    context.user_data['SO_date'] = date
    query.data = ccd('TRIP_ID', trip_key)

    return SO_review(update, context)

def RSV_cancel(update, context):
    """Cancels reservation from notification conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('SO_'):
            del context.user_data[key]
    query.edit_message_text(text="No se ha enviado la solicitud de reserva.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    regex_iso_date = '([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])'
    adl = list(abbr_dir_dict.keys())    # Abbreviated directions list
    dir_aux = f"({adl[0]}|{adl[1]})"

    # Create conversation handler for 'see offers'
    SO_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('verofertas', see_offers)],
        states={
            SO_START: [
                CallbackQueryHandler(SO_select_date, pattern=f"^{ccd(cdh,'DIR',dir_aux)}$"),
            ],
            SO_DATE: [
                CallbackQueryHandler(SO_select_hour, pattern=f"^{ccd(cdh,regex_iso_date)}$"),
            ],
            SO_HOUR: [
                CallbackQueryHandler(SO_select_hour_range_start, pattern=f"^{ccd(cdh,'RANGE')}$"),
                CallbackQueryHandler(SO_visualize, pattern=f"^{ccd(cdh,'ALL')}$"),
            ],
            SO_HOUR_SELECT_RANGE_START: [
                CallbackQueryHandler(SO_select_hour_range_stop, pattern="^TIME_PICKER.*"),
                MessageHandler(Filters.text & ~Filters.command, SO_select_hour_range_stop),
            ],
            SO_HOUR_SELECT_RANGE_STOP: [
                CallbackQueryHandler(SO_visualize, pattern="^TIME_PICKER.*"),
                MessageHandler(Filters.text & ~Filters.command, SO_visualize),
            ],
            SO_VISUALIZE: [
                CallbackQueryHandler(SO_review, pattern="^TRIP_ID[^\ \n]*"),
                CallbackQueryHandler(SO_end, pattern=f"^{ccd(cdh,'CANCEL')}$"),
            ],
            SO_REVIEW: [
                CallbackQueryHandler(SO_reserve, pattern=f"^{ccd(cdh,'CONFIRM_RSV')}$"),
                CallbackQueryHandler(SO_visualize, pattern=f"^{ccd(cdh,'CANCEL')}$"),
            ]
        },
        fallbacks=[CallbackQueryHandler(SO_cancel, pattern=f"^{ccd(cdh,'CANCEL')}$"),
                   CommandHandler('verofertas', see_offers)],
    )

    dispatcher.add_handler(SO_conv_handler)

    # Create Callback Query handler for 'alert user'
    dispatcher.add_handler(CallbackQueryHandler(alert_user, pattern="^ALERT.*"))

    # Create Callback Query handler for 'reserve from notification'
    RSV_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(reserve_from_notification, pattern="^RSV.*")],
        states={SO_REVIEW: [
                CallbackQueryHandler(SO_reserve, pattern=f"^{ccd(cdh,'CONFIRM_RSV')}$"),
                ]},
        fallbacks=[CallbackQueryHandler(RSV_cancel, pattern=f"^{ccd(cdh,'CANCEL')}$")],
    )
    dispatcher.add_handler(RSV_conv_handler)
