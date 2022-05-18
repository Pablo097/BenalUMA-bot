import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import add_trip, get_fee, get_slots
from messages.format import format_trip_from_data, get_formatted_trip_for_driver
from messages.notifications import notify_new_trip
from utils.keyboards import weekdays_keyboard
from utils.time_picker import (time_picker_keyboard, process_time_callback)
from utils.common import *
from utils.decorators import registered, driver

# 'New trip' conversation points
(TRIP_START, TRIP_DATE, TRIP_HOUR, TRIP_SELECT_MORE,
                TRIP_CHANGING_SLOTS, TRIP_CHANGING_PRICE) = range(6)
cdh = "NT"   # Callback Data Header

# Abort/Cancel buttons
ikbs_abort_trip = [[InlineKeyboardButton("Abortar", callback_data=ccd(cdh,'ABORT'))]]

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
    keyboard = [[InlineKeyboardButton("Hacia la UMA", callback_data=ccd(cdh,opt,'UMA')),
                 InlineKeyboardButton("Hacia Benalmádena", callback_data=ccd(cdh,opt,'BEN'))]]
    keyboard += ikbs_abort_trip
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
        
    if data[2] == "UMA":
        context.user_data['trip_dir'] = 'toUMA'
    elif data[2] == "BEN":
        context.user_data['trip_dir'] = 'toBenalmadena'
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
    text = f"Ahora dime, ¿a qué hora pretendes salir desde "\
           f"{'Benalmádena' if context.user_data['trip_dir']=='toUMA' else 'la UMA'}?"\
           f"\n(También puedes mandarme un mensaje con la hora directamente)"
    reply_markup = time_picker_keyboard(ikbs_list=ikbs_abort_trip)
    query.edit_message_text(text=text, reply_markup=reply_markup)

    return TRIP_HOUR

def send_select_more_message(update, context):
    dir = context.user_data['trip_dir']
    date = context.user_data['trip_date']
    time = context.user_data['trip_time']
    slots = context.user_data['trip_slots'] if 'trip_slots' in context.user_data else None
    price = context.user_data['trip_price'] if 'trip_price' in context.user_data else None

    keyboard = [[InlineKeyboardButton("Configurar asientos", callback_data=ccd(cdh,"SLOTS"))],
                [InlineKeyboardButton("Configurar precio", callback_data=ccd(cdh,"PRICE"))],
                [InlineKeyboardButton("Terminar", callback_data=ccd(cdh,"DONE"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Tu viaje se publicará con los siguientes datos:\n\n"
    text = escape_markdown(text, 2)
    text += format_trip_from_data(dir, date, time=time, slots=slots, fee=price)
    text2 = f"\n\nPuedes especificar los asientos disponibles y/o el precio"\
            f" para este viaje en particular si lo deseas. Si no, se usarán"\
            f" los valores por defecto de tu configuración de conductor."
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

def selecting_more(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the selecting_more function.')

    if data[1] == 'SLOTS':
        slots_default = get_slots(update.effective_chat.id)

        text_default = f"Usar asientos por defecto ({emoji_numbers[slots_default]})"
        keyboard = [[
                 InlineKeyboardButton(emoji_numbers[1], callback_data=ccd(cdh,"1")),
                 InlineKeyboardButton(emoji_numbers[2], callback_data=ccd(cdh,"2")),
                 InlineKeyboardButton(emoji_numbers[3], callback_data=ccd(cdh,"3"))],
                [InlineKeyboardButton(emoji_numbers[4], callback_data=ccd(cdh,"4")),
                 InlineKeyboardButton(emoji_numbers[5], callback_data=ccd(cdh,"5")),
                 InlineKeyboardButton(emoji_numbers[6], callback_data=ccd(cdh,"6"))],
                [InlineKeyboardButton(text_default, callback_data=ccd(cdh,'SLOTS_DEFAULT'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "¿Cuántos asientos disponibles quieres ofertar para este viaje?"
        context.user_data['trip_setting'] = 'slots'
        next_state = TRIP_CHANGING_SLOTS
    elif data[1] == 'PRICE':
        price_default = str(get_fee(update.effective_chat.id)).replace('.',',')

        text_default = f"Usar precio por defecto ({price_default}€)"
        keyboard = [[InlineKeyboardButton(text_default, callback_data=ccd(cdh,'PRICE_DEFAULT'))]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        text = "Escribe el precio por pasajero para este trayecto (máximo 1,5€)."
        context.user_data['trip_setting'] = 'price'
        next_state = TRIP_CHANGING_PRICE

    query.edit_message_text(text=text, reply_markup=reply_markup)
    return next_state

def update_trip_setting(update, context):
    # Check if update is callback query or new message
    if update.callback_query:
        is_query = True
        query = update.callback_query
    else:
        is_query = False

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the update_trip_setting function.')

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
    trip_key = add_trip(dir, update.effective_chat.id, date, time, slots, price)

    text = escape_markdown("Perfecto. ¡Tu viaje se ha publicado!\n\n",2)
    text += get_formatted_trip_for_driver(dir, date, trip_key)
    query.edit_message_text(text=text, parse_mode=telegram.ParseMode.MARKDOWN_V2)

    notify_new_trip(context, dir, update.effective_chat.id, date, time, slots, price)

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

    # Create conversation handler for 'new trip'
    trip_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevoviaje', new_trip)],
        states={
            TRIP_START: [
                CallbackQueryHandler(select_date, pattern=f"^{ccd(cdh,'DIR','(UMA|BEN)')}$"),
            ],
            TRIP_DATE: [
                CallbackQueryHandler(select_hour, pattern=f"^{ccd(cdh,regex_iso_date)}$"),
            ],
            TRIP_HOUR: [
                CallbackQueryHandler(select_more, pattern='^TIME_PICKER.*'),
                MessageHandler(Filters.text & ~Filters.command, select_more),
            ],
            TRIP_SELECT_MORE: [
                CallbackQueryHandler(selecting_more, pattern=f"^{ccd(cdh,'(SLOTS|PRICE)')}$"),
                CallbackQueryHandler(publish_trip, pattern=f"^{ccd(cdh,'DONE')}$"),
            ],
            TRIP_CHANGING_SLOTS: [
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'(1|2|3|4|5|6)')}$"),
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'SLOTS_DEFAULT')}$"),
            ],
            TRIP_CHANGING_PRICE: [
                CallbackQueryHandler(update_trip_setting, pattern=f"^{ccd(cdh,'PRICE_DEFAULT')}$"),
                MessageHandler(Filters.text & ~Filters.command, update_trip_setting),
            ]
        },
        fallbacks=[CallbackQueryHandler(trip_abort, pattern=f"^{ccd(cdh,'ABORT')}$"),
                   CommandHandler('nuevoviaje', new_trip)],
    )

    dispatcher.add_handler(trip_conv_handler)
