import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (add_trip, get_fee, get_slots, get_request_time,
                                get_home, get_univ)
from messages.format import (format_trip_from_data, get_formatted_trip_for_driver,
                            get_actual_origin, get_actual_dest)
from messages.notifications import notify_new_trip
from utils.keyboards import weekdays_keyboard, seats_keyboard
from utils.time_picker import (time_picker_keyboard, process_time_callback)
from utils.common import *
from utils.decorators import registered, driver

# 'New trip' conversation points
(TRIP_START, TRIP_DATE, TRIP_HOUR, TRIP_SELECT_MORE, TRIP_CHANGING_SLOTS,
    TRIP_CHANGING_PRICE, TRIP_CHANGING_ORIGIN, TRIP_CHANGING_DEST) = range(8)
cdh = "NT"   # Callback Data Header

# Abort/Cancel buttons
ikbs_abort_trip = [[InlineKeyboardButton("❌ Abortar", callback_data=ccd(cdh,'ABORT'))]]

logger = logging.getLogger(__name__)

@driver
@registered
def new_trip(update, context):
    """Gives options for offering a new trip"""
    # Check if command was previously called and remove reply markup associated
    if 'trip_message' in context.user_data:
        sent_message = context.user_data.pop('trip_message')
        sent_message.edit_reply_markup(None)
    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('trip_'):
            del context.user_data[key]

    opt = "DIR"
    row = []
    for dir in dir_dict2:
        row.append(InlineKeyboardButton(f"Hacia {dir_dict2[dir]}",
                                    callback_data=ccd(cdh,opt,dir[2:5].upper())))
    keyboard = [row] + ikbs_abort_trip
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Vas a ofertar un nuevo viaje. Primero, indica en qué dirección viajas:"
    context.user_data['trip_message'] = update.message.reply_text(text,
                                                reply_markup=reply_markup)
    return TRIP_START

def select_date(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='DIR'):
        raise SyntaxError('This callback data does not belong to the select_date function.')

    if data[2] in abbr_dir_dict:
        context.user_data['trip_dir'] = abbr_dir_dict[data[2]]
    else:
        logger.warning("Error in trip direction argument.")
        text = f"Error en opción recibida. Abortando..."
        query.edit_message_text(text=text, reply_markup=None)
        return ConversationHandler.END

    reply_markup = weekdays_keyboard(cdh, ikbs_list=ikbs_abort_trip)
    text = f"De acuerdo. ¿Para qué día vas a ofertar el viaje?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return TRIP_DATE

def select_hour(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the select_hour function.')

    context.user_data['trip_date'] = data[1]
    text_aux = 'salir'
    if context.user_data['trip_dir']==list(dir_dict.keys())[0]:
        text_aux = f"llegar a {dir_dict2[context.user_data['trip_dir']]}"
    elif context.user_data['trip_dir']==list(dir_dict.keys())[1]:
        text_aux = f"salir hacia {dir_dict2[context.user_data['trip_dir']]}"
    text = f"Ahora dime, ¿a qué hora pretendes {text_aux}?"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_abort_trip)
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return TRIP_HOUR

def send_select_more_message(update, context):
    dir = context.user_data['trip_dir']
    date = context.user_data['trip_date']
    time = context.user_data['trip_time']
    slots = context.user_data.get('trip_slots', None)
    price = context.user_data.get('trip_price', None)
    origin = context.user_data.get('trip_origin',
                            get_actual_origin(update.effective_chat.id, dir))
    dest = context.user_data.get('trip_dest',
                            get_actual_dest(update.effective_chat.id, dir))

    keyboard = [[InlineKeyboardButton("💰 Precio", callback_data=ccd(cdh,"PRICE")),
                 InlineKeyboardButton("💺 Asientos", callback_data=ccd(cdh,"SLOTS"))],
                [InlineKeyboardButton("🚏 Origen", callback_data=ccd(cdh,"ORIGIN")),
                 InlineKeyboardButton("🏁 Destino", callback_data=ccd(cdh,"DEST"))],
                [ikbs_abort_trip[0][0],
                 InlineKeyboardButton("✅ Terminar", callback_data=ccd(cdh,"DONE"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Tu viaje se publicará con los siguientes datos:\n\n"
    text = escape_markdown(text, 2)
    text += format_trip_from_data(dir, date, time=time, slots=slots, fee=price,
                                            origin=origin, dest=dest)
    text2 = f"\n\nPuedes especificar cualquiera de los datos de abajo para este"\
            f" viaje en particular si lo deseas. Si no, se usarán los valores"\
            f" por defecto de tu configuración de conductor."
    text += escape_markdown(text2, 2)

    if update.callback_query:
        update.callback_query.edit_message_text(text=text, reply_markup=reply_markup,
                                parse_mode=telegram.ParseMode.MARKDOWN_V2)
    else:
        context.user_data['trip_message'] = update.message.reply_text(text=text,
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)

def select_more(update, context):
    time = process_time_callback(update, context, 'trip', ikbs_abort_trip)
    if not time:
        return TRIP_HOUR
    else:
        context.user_data['trip_time'] = time
        send_select_more_message(update, context)
    return TRIP_SELECT_MORE

def select_more_from_SR(update, context):
    query = update.callback_query
    query.answer()

    if 'SR_message' in context.user_data:
        context.user_data['trip_message'] = context.user_data.pop('SR_message')
    dir = context.user_data.pop('SR_dir')
    date = context.user_data.pop('SR_date')
    data = scd(query.data)
    if data[0] != 'REQ_ID':
        raise SyntaxError('This callback data does not belong to the select_more_from_SR function.')
    req_key = ';'.join(data[1:])   # Just in case the unique ID constains a ';'

    time = get_request_time(dir, date, req_key)
    context.user_data['trip_dir'] = dir
    context.user_data['trip_date'] = date
    context.user_data['trip_time'] = time
    send_select_more_message(update, context)

    return TRIP_SELECT_MORE

def selecting_more(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the selecting_more function.')

    if data[1] == 'SLOTS':
        slots_default = get_slots(update.effective_chat.id)

        text_default = f"Usar asientos por defecto ({emoji_numbers[slots_default]})"
        reply_markup = seats_keyboard(6, cdh,
            ikbs_list=[[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'SLOTS_DEFAULT'))]])

        text = "¿Cuántos asientos disponibles quieres ofertar para este viaje?"
        text = escape_markdown(text,2)
        context.user_data['trip_setting'] = 'slots'
        next_state = TRIP_CHANGING_SLOTS
    elif data[1] == 'PRICE':
        price_default = str(get_fee(update.effective_chat.id)).replace('.',',')

        text_default = f"Usar precio por defecto ({price_default}€)"
        keyboard = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'PRICE_DEFAULT'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"Escribe el precio por pasajero para este trayecto (máximo {str(MAX_FEE).replace('.',',')}€)."
        text = escape_markdown(text,2)
        context.user_data['trip_setting'] = 'price'
        next_state = TRIP_CHANGING_PRICE
    elif data[1] == 'ORIGIN':
        dir = context.user_data['trip_dir']
        if dir==list(dir_dict.keys())[0]:       # University
            origin = get_home(update.effective_chat.id)
            eg_list = home_examples_list
            dir_str = dir_dict2[list(dir_dict.keys())[1]]
        elif dir==list(dir_dict.keys())[1]:     # Home
            origin = get_univ(update.effective_chat.id)
            eg_list = univ_examples_list
            dir_str = dir_dict2[list(dir_dict.keys())[0]]

        text = f"Escribe una breve descripción de la *zona de la que vas a salir*\."\
               f" Por ejemplo: `{'`, `'.join([escape_markdown(aux,2) for aux in eg_list])}`"\
               f", etc\. \(Máximo {MAX_LOC_CHARS} caracteres\)"
        # If origin has a default value, give option to use it
        if origin:
            text_default = f"Usar origen por defecto ({escape_markdown(origin,2)})"
            keyboard = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'ORIGIN_DEFAULT'))]]
        else:
            text += f"\n\nRecuerda que puedes configurar una zona de {dir_str} por"\
                    f" defecto desde el comando /config, que los usuarios verán"\
                    f" en todos tus viajes para los que no hayas concretado una distinta\."
            keyboard = [[InlineKeyboardButton("Borrar", callback_data=ccd(cdh,'ORIGIN_DELETE'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data['trip_setting'] = 'origin'
        next_state = TRIP_CHANGING_ORIGIN
    elif data[1] == 'DEST':
        dir = context.user_data['trip_dir']
        dir_str = dir_dict2[dir]
        if dir==list(dir_dict.keys())[0]:       # University
            dest = get_univ(update.effective_chat.id)
            eg_list = univ_examples_list
        elif dir==list(dir_dict.keys())[1]:     # Home
            dest = get_home(update.effective_chat.id)
            eg_list = home_examples_list

        text = f"Escribe una breve descripción de la *zona a la que vas a ir*\."\
               f" Por ejemplo: `{'`, `'.join([escape_markdown(aux,2) for aux in eg_list])}`"\
               f", etc\. \(Máximo {MAX_LOC_CHARS} caracteres\)"
        # If destination has a default value, give option to use it
        if dest:
            text_default = f"Usar destino por defecto ({escape_markdown(dest,2)})"
            keyboard = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'DEST_DEFAULT'))]]
        else:
            text += f"\n\nRecuerda que puedes configurar una zona de {dir_str} por"\
                    f" defecto desde el comando /config, que los usuarios verán"\
                    f" en todos tus viajes para los que no hayas concretado una distinta\."
            keyboard = [[InlineKeyboardButton("Borrar", callback_data=ccd(cdh,'DEST_DELETE'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data['trip_setting'] = 'dest'
        next_state = TRIP_CHANGING_DEST

    query.edit_message_text(text=text, reply_markup=reply_markup,
                                    parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return next_state

def update_trip_setting(update, context):
    # Check if update is callback query or new message
    if update.callback_query:
        is_query = True
        query = update.callback_query
        data = scd(query.data)
        if data[0]!=cdh:
            raise SyntaxError('This callback data does not belong to the update_trip_setting function.')
    else:
        is_query = False

    setting = context.user_data.pop('trip_setting', None)
    if setting == 'slots':
        if data[1] == "SLOTS_DEFAULT":
            context.user_data.pop('trip_slots', None)
        else:
            context.user_data['trip_slots'] = int(data[1])
    elif setting == 'price':
        if not is_query:
            # Remove possible inline keyboard from previous message
            if 'trip_message' in context.user_data:
                sent_message = context.user_data.pop('trip_message')
                sent_message.edit_reply_markup(None)
            # Obtain price
            try:
                price = obtain_float_from_string(update.message.text)
            except:
                price = -1
            if not (price>=0 and price<=MAX_FEE):
                price_default = str(get_fee(update.effective_chat.id)).replace('.',',')

                text_default = f"Usar precio por defecto ({price_default}€)"
                keyboard = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'PRICE_DEFAULT'))]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                text = f"Por favor, introduce un número entre 0 y {str(MAX_FEE).replace('.',',')}."
                context.user_data['trip_message'] = update.message.reply_text(text,
                                                        reply_markup=reply_markup)
                context.user_data['trip_setting'] = 'price'
                return TRIP_CHANGING_PRICE
            else:
                context.user_data['trip_price'] = price
        elif data[1] == "PRICE_DEFAULT":
            context.user_data.pop('trip_price', None)
    elif setting == 'origin':
        if not is_query:
            # Remove possible inline keyboard from previous message
            if 'trip_message' in context.user_data:
                sent_message = context.user_data.pop('trip_message')
                sent_message.edit_reply_markup(None)
            # Obtain origin, limiting characters
            origin = update.message.text[:20].capitalize()
            context.user_data['trip_origin'] = origin
        elif data[1] == "ORIGIN_DEFAULT" or data[1] == "ORIGIN_DELETE":
            context.user_data.pop('trip_origin', None)
    elif setting == 'dest':
        if not is_query:
            # Remove possible inline keyboard from previous message
            if 'trip_message' in context.user_data:
                sent_message = context.user_data.pop('trip_message')
                sent_message.edit_reply_markup(None)
            # Obtain destination, limiting characters
            dest = update.message.text[:20].capitalize()
            context.user_data['trip_dest'] = dest
        elif data[1] == "DEST_DEFAULT" or data[1] == "DEST_DELETE":
            context.user_data.pop('trip_dest', None)

    send_select_more_message(update, context)
    return TRIP_SELECT_MORE

def publish_trip(update, context):
    query = update.callback_query
    query.answer()

    dir = context.user_data.pop('trip_dir')
    date = context.user_data.pop('trip_date')
    time = context.user_data.pop('trip_time')
    slots = context.user_data.pop('trip_slots', None)
    price = context.user_data.pop('trip_price', None)
    origin = context.user_data.pop('trip_origin', None)
    dest = context.user_data.pop('trip_dest', None)
    trip_key = add_trip(dir, update.effective_chat.id, date, time, slots,
                                                        price, origin, dest)

    text = escape_markdown("Perfecto. ¡Tu viaje se ha publicado!\n\n",2)
    text += get_formatted_trip_for_driver(dir, date, trip_key)
    query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)

    notify_new_trip(context, trip_key, dir, update.effective_chat.id, date,
                            time, slots, price, origin, dest)

    for key in list(context.user_data.keys()):
        if key.startswith('trip_'):
            del context.user_data[key]
    return ConversationHandler.END

def trip_abort(update, context):
    """Aborts trip conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('trip_'):
            del context.user_data[key]
    query.edit_message_text(text="La creación de una nueva oferta de viaje se ha abortado.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    regex_iso_date = '([0-9]{4})-(1[0-2]|0[1-9])-(3[01]|0[1-9]|[12][0-9])'
    adl = list(abbr_dir_dict.keys())    # Abbreviated directions list
    dir_aux = f"({adl[0]}|{adl[1]})"

    # Create conversation handler for 'new trip'
    global trip_conv_handler
    trip_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevoviaje', new_trip),
                      CallbackQueryHandler(select_more_from_SR, pattern="^REQ_ID[^\ \n]*")],
        states={
            TRIP_START: [
                CallbackQueryHandler(select_date, pattern=f"^{ccd(cdh,'DIR',dir_aux)}$"),
            ],
            TRIP_DATE: [
                CallbackQueryHandler(select_hour, pattern=f"^{ccd(cdh,regex_iso_date)}$"),
            ],
            TRIP_HOUR: [
                CallbackQueryHandler(select_more, pattern='^TIME_PICKER.*'),
                MessageHandler(Filters.text & ~Filters.command, select_more),
            ],
            TRIP_SELECT_MORE: [
                CallbackQueryHandler(selecting_more, pattern=f"^{ccd(cdh,'(SLOTS|PRICE|ORIGIN|DEST)')}$"),
                CallbackQueryHandler(publish_trip, pattern=f"^{ccd(cdh,'DONE')}$"),
            ],
            TRIP_CHANGING_SLOTS: [
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'(1|2|3|4|5|6)')}$"),
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'SLOTS_DEFAULT')}$"),
            ],
            TRIP_CHANGING_PRICE: [
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'PRICE_DEFAULT')}$"),
                MessageHandler(Filters.text & ~Filters.command, update_trip_setting),
            ],
            TRIP_CHANGING_ORIGIN: [
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'ORIGIN_(DELETE|DEFAULT)')}$"),
                MessageHandler(Filters.text & ~Filters.command, update_trip_setting),
            ],
            TRIP_CHANGING_DEST: [
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'DEST_(DELETE|DEFAULT)')}$"),
                MessageHandler(Filters.text & ~Filters.command, update_trip_setting),
            ],
        },
        fallbacks=[CallbackQueryHandler(trip_abort, pattern=f"^{ccd(cdh,'ABORT')}$"),
                   CommandHandler('nuevoviaje', new_trip)],
        map_to_parent={
            # Mapping for when this conversation handler is nested inside the
            # 'see requests' conversation handler
            ConversationHandler.END: ConversationHandler.END
        }
    )

    dispatcher.add_handler(trip_conv_handler)
