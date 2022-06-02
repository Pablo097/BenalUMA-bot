import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (delete_trip, remove_passenger, get_fee, get_slots,
                                get_trip_passengers, get_trip_time,
                                get_number_of_passengers, get_trip_fee,
                                set_trip_fee, set_trip_slots)
from messages.format import (get_markdown2_inline_mention,
                          get_formatted_trip_for_driver,
                          get_driver_week_formatted_trips)
from messages.notifications import delete_trip_notify, remove_passenger_notify
from utils.keyboards import trips_keyboard, passengers_keyboard, seats_keyboard
from utils.common import *
from utils.decorators import registered, driver, send_typing_action

(MYTRIPS_SELECT, MYTRIPS_EDIT, MYTRIPS_EDITING, MYTRIPS_CHANGING_SLOTS,
    MYTRIPS_CHANGING_PRICE, MYTRIPS_CANCEL, MYTRIPS_REJECT, MYTRIPS_EXECUTE) = range(10,18)
cdh = 'MT'   # Callback Data Header

# Abort/Cancel buttons
ikbs_end_MT = [[InlineKeyboardButton("Terminar", callback_data=ccd(cdh,"END"))]]
ikbs_back_MT = [[InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK"))]]

logger = logging.getLogger(__name__)

@send_typing_action
@driver
@registered
def my_trips(update, context):
    """Shows all the offered trips for the week ahead"""
    # Check if command was previously called and remove reply markup associated
    if 'MT_message' in context.user_data:
        sent_message = context.user_data.pop('MT_message')
        sent_message.edit_reply_markup(None)
    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('MT_'):
            del context.user_data[key]

    formatted_trips, trips_dict = get_driver_week_formatted_trips(update.effective_chat.id)
    if trips_dict:
        text = f"Viajes ofertados para los próximos 7 días:\n\n{formatted_trips}"
        context.user_data['MT_dict'] = trips_dict
        keyboard = [[InlineKeyboardButton("Editar viaje", callback_data=ccd(cdh,"EDIT")),
                     InlineKeyboardButton("Anular viaje", callback_data=ccd(cdh,"CANCEL"))],
                    [InlineKeyboardButton("Expulsar pasajero", callback_data=ccd(cdh,"REJECT"))]]
        keyboard += ikbs_end_MT
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.user_data['MT_message'] = update.message.reply_text(text,
                reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return MYTRIPS_SELECT
    else:
        text = "No tienes viajes ofertados para la próxima semana."
        update.message.reply_text(text)
    return ConversationHandler.END

@send_typing_action
def my_trips_restart(update, context):
    """Shows all the offered trips for the week ahead"""
    query = update.callback_query
    query.answer()

    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('MT_') and key!='MT_message':
            del context.user_data[key]

    formatted_trips, trips_dict = get_driver_week_formatted_trips(update.effective_chat.id)
    if trips_dict:
        text = f"Viajes ofertados para los próximos 7 días:\n\n{formatted_trips}"
        context.user_data['MT_dict'] = trips_dict
        keyboard = [[InlineKeyboardButton("Editar viaje", callback_data=ccd(cdh,"EDIT")),
                     InlineKeyboardButton("Anular viaje", callback_data=ccd(cdh,"CANCEL"))],
                    [InlineKeyboardButton("Expulsar pasajero", callback_data=ccd(cdh,"REJECT"))]]
        keyboard += ikbs_end_MT
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
        return MYTRIPS_SELECT
    else:
        text = "No tienes viajes ofertados para la próxima semana."
        query.edit_message_text(text)
    return ConversationHandler.END

def choose_trip(update, context):
    """Lets user pick the trip to edit"""
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the choose_trip function.')

    trips_dict = context.user_data['MT_dict']
    if data[1] == "EDIT":
        next_state = MYTRIPS_EDIT
        text = f"¿Qué viaje quieres editar?"
        reply_markup = trips_keyboard(trips_dict, cdh, ikbs_back_MT,
                                                show_passengers=False)
    elif data[1] == "CANCEL":
        next_state = MYTRIPS_CANCEL
        text = f"¿Qué viaje quieres anular?"
        reply_markup = trips_keyboard(trips_dict, cdh, ikbs_back_MT,
                                show_extra_param=False, show_passengers=False)
    elif data[1] == "REJECT":
        next_state = MYTRIPS_REJECT
        # Filter trips with passengers
        trips_dict_with_passengers = dict()
        for date in trips_dict:
            date_dict = dict()
            for key in trips_dict[date]:
                if 'Passengers' in trips_dict[date][key]:
                    date_dict[key] = trips_dict[date][key]
            if date_dict:
                trips_dict_with_passengers[date] = date_dict
        # Message dependent on whether there are passengers or not
        if trips_dict_with_passengers:
            reply_markup = trips_keyboard(trips_dict_with_passengers, cdh,
                                        ikbs_back_MT, show_extra_param=False)
            text = f"Elige el viaje del que quieras expulsar a un pasajero:"
        else:
            reply_markup = InlineKeyboardMarkup(ikbs_back_MT)
            text = f"Ninguno de tus viajes tiene aún pasajeros aceptados."

    query.edit_message_text(text, reply_markup=reply_markup)
    return next_state

def edit_trip(update, context):
    """Gives options for changing the trip parameters"""
    query = update.callback_query
    query.answer()

    # Parse trip identifiers
    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='ID'):
        raise SyntaxError('This callback data does not belong to the edit_trip function.')
    direction = data[2]
    date = data[3]
    trip_key = ';'.join(data[4:])   # Just in case the unique ID constains a ';'
    direction = abbr_dir_dict[direction]

    # Save trip parameters
    context.user_data['MT_dir'] = direction
    context.user_data['MT_date'] = date
    context.user_data['MT_key'] = trip_key

    opt = 'EDIT'
    keyboard = [[InlineKeyboardButton("💰 Precio", callback_data=ccd(cdh,opt,"PRICE")),
                 InlineKeyboardButton("💺 Asientos", callback_data=ccd(cdh,opt,"SLOTS"))]]
    keyboard += ikbs_back_MT
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = escape_markdown(f"¿Qué parámetros quieres cambiar o añadir?\n\n",2)
    text += get_formatted_trip_for_driver(direction, date, trip_key)
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return MYTRIPS_EDITING

def edit_property(update, context):
    """Gives options to change the selected property of the trip"""
    query = update.callback_query
    query.answer()

    # Parse trip identifiers
    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='EDIT'):
        raise SyntaxError('This callback data does not belong to the change_trip_property function.')

    dir = context.user_data['MT_dir']
    date = context.user_data['MT_date']
    key = context.user_data['MT_key']

    if data[2] == 'SLOTS':
        slots_default = get_slots(update.effective_chat.id)
        num_passengers = get_number_of_passengers(dir, date, key)
        if num_passengers > slots_default:
            ikbs_list = None
        else:
            text_default = f"Usar asientos por defecto ({emoji_numbers[slots_default]})"
            ikbs_list = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'SLOTS_DEFAULT'))]]

        min_slots = max(num_passengers, 1)
        reply_markup = seats_keyboard(6, cdh, min_slots, ikbs_list=ikbs_list)

        text = f"¿Cuántos asientos disponibles quieres ofertar para este viaje?"\
               f"\n(Sólo puedes modificar los asientos para que haya igual o más"\
               " que el número de pasajeros que ya tengas aceptados)"
        context.user_data['MT_edit_option'] = 'slots'
        next_state = MYTRIPS_CHANGING_SLOTS
    elif data[2] == 'PRICE':
        user_fee = get_fee(update.effective_chat.id)
        num_passengers = get_number_of_passengers(dir, date, key)
        text = f"Escribe el nuevo precio por pasajero para este trayecto"
        # If passengers already in trip, fee can't be risen from the current value
        if num_passengers>0:
            trip_fee = get_trip_fee(dir, date, key)
            max_fee = trip_fee if trip_fee!=None else user_fee
            text += f". Como ya tienes pasajeros reservados, no puedes subir"\
                    f" el precio del que ya tenías configurado ("
        else:
            trip_fee = None
            max_fee = MAX_FEE
            text += f" (máximo "
        text += f"{str(max_fee).replace('.',',')}€)."
        # Only give option to go back to default fee if there is no trip fee or
        # it is higher than the default user value
        if not trip_fee or (trip_fee and trip_fee >= user_fee):
            price_default = str(user_fee).replace('.',',')
            text_default = f"Usar precio por defecto ({price_default}€)"
            keyboard = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'PRICE_DEFAULT'))]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        else:
            reply_markup = None

        context.user_data['MT_edit_option'] = 'price'
        context.user_data['MT_max_fee'] = max_fee
        next_state = MYTRIPS_CHANGING_PRICE

    context.user_data['MT_message'] = query.edit_message_text(text, reply_markup=reply_markup)
    return next_state

def update_trip_property(update, context):
    # Check if update is callback query or new message
    if update.callback_query:
        is_query = True
        query = update.callback_query
        data = scd(query.data)
        if data[0]!=cdh:
            raise SyntaxError('This callback data does not belong to the update_trip_property function.')
    else:
        is_query = False

    # Obtain trip parameters
    direction = context.user_data['MT_dir']
    date = context.user_data['MT_date']
    trip_key = context.user_data['MT_key']
    option = context.user_data.pop('MT_edit_option', None)

    if option == 'slots':
        if data[1] == "SLOTS_DEFAULT":
            set_trip_slots(direction, date, trip_key)
        else:
            set_trip_slots(direction, date, trip_key, int(data[1]))
    elif option == 'price':
        max_fee = context.user_data['MT_max_fee']
        if not is_query:
            reply_markup = None
            # Remove possible inline keyboard from previous message
            if 'MT_message' in context.user_data:
                sent_message = context.user_data.pop('MT_message')
                if sent_message.reply_markup:
                    sent_message.edit_reply_markup(None)
                    reply_markup = sent_message.reply_markup
            # Obtain price
            try:
                price = obtain_float_from_string(update.message.text)
            except:
                price = -1
            if not (price>=0 and price<=max_fee):
                text = f"Por favor, introduce un número entre 0 y {str(max_fee).replace('.',',')}."
                context.user_data['MT_message'] = update.message.reply_text(text,
                                                        reply_markup=reply_markup)
                context.user_data['MT_edit_option'] = 'price'
                return MYTRIPS_CHANGING_PRICE
            else:
                set_trip_fee(direction, date, trip_key, price)
        elif data[1] == "PRICE_DEFAULT":
            set_trip_fee(direction, date, trip_key)

    opt = 'EDIT'
    keyboard = [[InlineKeyboardButton("💰 Precio", callback_data=ccd(cdh,opt,"PRICE")),
                 InlineKeyboardButton("💺 Asientos", callback_data=ccd(cdh,opt,"SLOTS"))]]
    keyboard += ikbs_back_MT
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Los parámetros de tu viaje han sido cambiados correctamente."\
           f" ¿Quieres cambiar algo más?\n\n"
    text = escape_markdown(text,2)
    text += get_formatted_trip_for_driver(direction, date, trip_key)
    if is_query:
        query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    else:
        context.user_data['MT_message'] = update.message.reply_text(text,
                                            reply_markup=reply_markup,
                                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return MYTRIPS_EDITING

def cancel_trip(update, context):
    """Cancels the given trip"""
    query = update.callback_query
    query.answer()

    # Parse trip identifiers
    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='ID'):
        raise SyntaxError('This callback data does not belong to the cancel_trip function.')
    direction = data[2]
    date = data[3]
    trip_key = ';'.join(data[4:])   # Just in case the unique ID constains a ';'
    direction = abbr_dir_dict[direction]

    # Save trip parameters
    context.user_data['MT_dir'] = direction
    context.user_data['MT_date'] = date
    context.user_data['MT_key'] = trip_key

    # Check if trip hasn't ocurred yet
    time = get_trip_time(direction, date, trip_key)
    if not is_future_datetime(date, time, 15):
        reply_markup = InlineKeyboardMarkup(ikbs_back_MT)
        text = f"🚫 No puedes eliminar este viaje porque ya ha pasado\."
    else:
        keyboard = [[InlineKeyboardButton("✔️ Sí, eliminar", callback_data=ccd(cdh,"CANCEL_CONFIRM")),
                     ikbs_back_MT[0][0]]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = f"Vas a eliminar el siguiente viaje:\n\n"
        text += get_formatted_trip_for_driver(direction, date, trip_key)
        text += f"\n\n¿Estás seguro?"
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return MYTRIPS_EXECUTE

def reject_passenger(update, context):
    """Lets user pick the trip to cancel"""
    query = update.callback_query
    query.answer()

    # Parse trip identifiers
    data = scd(query.data)
    if not (data[0]==cdh and data[1]=='ID'):
        raise SyntaxError('This callback data does not belong to the reject_passenger function.')
    direction = data[2]
    date = data[3]
    trip_key = ';'.join(data[4:])   # Just in case the unique ID constains a ';'
    direction = abbr_dir_dict[direction]

    # Save trip parameters
    context.user_data['MT_dir'] = direction
    context.user_data['MT_date'] = date
    context.user_data['MT_key'] = trip_key

    # Check if trip hasn't ocurred yet
    time = get_trip_time(direction, date, trip_key)
    if not is_future_datetime(date, time, 15):
        reply_markup = InlineKeyboardMarkup(ikbs_back_MT)
        text = f"🚫 No puedes expulsar pasajeros de este viaje porque ya ha pasado\."
    else:
        reply_markup = passengers_keyboard(
                        get_trip_passengers(direction, date, trip_key), cdh, ikbs_back_MT)
        text = f"Has seleccionado el siguiente viaje:\n\n"
        text += get_formatted_trip_for_driver(direction, date, trip_key)
        text += f"\n\n¿A qué pasajero quieres expulsar?"
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return MYTRIPS_EXECUTE

def MT_execute_action(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the MT_execute_action function.')

    # Obtain trip parameters
    direction = context.user_data.pop('MT_dir')
    date = context.user_data.pop('MT_date')
    trip_key = context.user_data.pop('MT_key')

    # Check action to execute
    if data[1] == "CANCEL_CONFIRM":
        delete_trip_notify(update, context, direction, date, trip_key)
        text = escape_markdown(f"Tu viaje ha sido anulado correctamente.",2)
    elif data[1] == 'PASS_ID':
        passenger_id = data[2]
        remove_passenger_notify(update, context, passenger_id, direction, date, trip_key)
        # Text for driver
        text = f"Has expulsado a {get_markdown2_inline_mention(passenger_id)}"\
               f" del siguiente viaje:\n\n"
        text += get_formatted_trip_for_driver(direction, date, trip_key)

    # Remove elements from user's dictionary
    for key in list(context.user_data.keys()):
        if key.startswith('MT_'):
            del context.user_data[key]

    query.edit_message_text(text, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return ConversationHandler.END

def MT_end(update, context):
    """Ends my trips conversation."""
    query = update.callback_query
    query.answer()
    for key in list(context.user_data.keys()):
        if key.startswith('MT_'):
            del context.user_data[key]
    query.edit_message_reply_markup(None)
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for 'my trips'
    ny_trips_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('misviajes', my_trips)],
        states={
            MYTRIPS_SELECT: [
                CallbackQueryHandler(choose_trip, pattern=f"^{ccd(cdh,'(EDIT|CANCEL|REJECT)')}$")
            ],
            MYTRIPS_EDIT: [
                CallbackQueryHandler(edit_trip, pattern=f"^{ccd(cdh,'ID','.*')}")
            ],
            MYTRIPS_EDITING: [
                CallbackQueryHandler(edit_property, pattern=f"^{ccd(cdh,'EDIT','(PRICE|SLOTS)')}$")
            ],
            MYTRIPS_CHANGING_SLOTS: [
                CallbackQueryHandler(update_trip_property, pattern=f"^{ccd(cdh,'(1|2|3|4|5|6)')}$"),
                CallbackQueryHandler(update_trip_property, pattern=f"^{ccd(cdh,'SLOTS_DEFAULT')}$"),
            ],
            MYTRIPS_CHANGING_PRICE: [
                CallbackQueryHandler(update_trip_property, pattern=f"^{ccd(cdh,'PRICE_DEFAULT')}$"),
                MessageHandler(Filters.text & ~Filters.command, update_trip_property),
            ],
            MYTRIPS_CANCEL: [
                CallbackQueryHandler(cancel_trip, pattern=f"^{ccd(cdh,'ID','.*')}")
            ],
            MYTRIPS_REJECT: [
                CallbackQueryHandler(reject_passenger, pattern=f"^{ccd(cdh,'ID','.*')}")
            ],
            MYTRIPS_EXECUTE: [
                CallbackQueryHandler(MT_execute_action, pattern=f"^{ccd(cdh,'CANCEL_CONFIRM')}$"),
                CallbackQueryHandler(MT_execute_action, pattern=f"^{ccd(cdh,'PASS_ID','.*')}")
            ]
        },
        fallbacks=[CallbackQueryHandler(my_trips_restart, pattern=f"^{ccd(cdh,'BACK')}$"),
                   CallbackQueryHandler(MT_end, pattern=f"^{ccd(cdh,'END')}$"),
                   CommandHandler('misviajes', my_trips)],
    )

    dispatcher.add_handler(ny_trips_conv_handler)
