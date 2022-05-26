import logging, telegram, re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                        ConversationHandler, CallbackContext, CallbackQueryHandler)
from telegram.utils.helpers import escape_markdown
from data.database_api import (is_registered, is_driver, set_name, set_car,
                                set_slots, set_bizum, set_fee, add_driver,
                                modify_offer_notification, modify_request_notification)
from messages.format import get_formatted_user_config
from messages.notifications import (delete_driver_notify, delete_user_notify,
                                    debug_group_notify)
from utils.keyboards import config_keyboard
from utils.common import *
from utils.decorators import registered

(CONFIG_SELECT, CONFIG_SELECT_ADVANCED, CHANGING_MESSAGE,
    CHANGING_SLOTS, CHANGING_BIZUM, CHOOSING_ADVANCED_OPTION) = range(6)
cdh = 'CONFIG'   # Callback Data Header

logger = logging.getLogger(__name__)

@registered
def config(update, context):
    """Gives options for changing the user configuration"""
    # Check if command was previously called and remove reply markup associated
    if 'config_message' in context.user_data:
        sent_message = context.user_data.pop('config_message')
        sent_message.edit_reply_markup(None)

    reply_markup = config_keyboard(update.effective_chat.id)

    text = f"Aquí puedes modificar la configuración asociada a tu cuenta\."
    text += f"\n\n Esta es tu configuración actual: \n"
    text += f"{get_formatted_user_config(update.effective_chat.id)} \n"
    context.user_data['config_message'] = update.message.reply_text(text,
            reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return CONFIG_SELECT

def config_restart(update, context):
    """Gives options for changing the user configuration"""
    query = update.callback_query
    query.answer()

    # Delete possible previous data
    for key in list(context.user_data.keys()):
        if key.startswith('config_') and key!='config_message':
            del context.user_data[key]

    reply_markup = config_keyboard(update.effective_chat.id)

    text = f"Esta es tu configuración actual: \n"
    text += get_formatted_user_config(update.effective_chat.id)
    text += f"\n\nPuedes seguir cambiando ajustes\."
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return CONFIG_SELECT

def config_select_advanced(update, context):
    """Gives advanced options for changing the user configuration"""
    query = update.callback_query
    query.answer()
    role = 'Pasajero' if is_driver(update.effective_chat.id) else 'Conductor'
    keyboard = [
        [
            InlineKeyboardButton(f"Cambiar rol a {role}", callback_data=ccd(cdh,"ROLE")),
        ],
        [
            InlineKeyboardButton("Eliminar cuenta", callback_data=ccd(cdh,"DELETE_ACCOUNT")),
        ],
        [
            InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK")),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['role'] = role
    text = f"Aquí puedes cambiar algunos ajustes avanzados."
    query.edit_message_text(text, reply_markup=reply_markup)
    return CONFIG_SELECT_ADVANCED

def change_name(update, context):
    """Lets user change their username"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK"))]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"⚠️ AVISO: Tu nombre y apellidos ayudan a los demás usuarios a reconocerte,"\
           f" así que deberías intentar no cambiarlos. \nSi aún así quieres cambiarlos"\
           f" (quizás porque te hubieras equivocado al registrarte), por favor,"\
           f" mándame de nuevo tu nombre y apellidos."
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'name'
    return CHANGING_MESSAGE

def config_slots(update, context):
    """Lets driver change their predefined available slots"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton(emoji_numbers[1], callback_data=ccd(cdh,"1")),
            InlineKeyboardButton(emoji_numbers[2], callback_data=ccd(cdh,"2")),
            InlineKeyboardButton(emoji_numbers[3], callback_data=ccd(cdh,"3")),
        ],
        [
            InlineKeyboardButton(emoji_numbers[4], callback_data=ccd(cdh,"4")),
            InlineKeyboardButton(emoji_numbers[5], callback_data=ccd(cdh,"5")),
            InlineKeyboardButton(emoji_numbers[6], callback_data=ccd(cdh,"6")),
        ],
        [
            InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK")),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "¿Cuántos asientos disponibles sueles ofertar?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'slots'
    return CHANGING_SLOTS

def config_bizum(update, context):
    """Lets driver change their Bizum preference"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Sí", callback_data=ccd(cdh,"YES")),
            InlineKeyboardButton("No", callback_data=ccd(cdh,"NO")),
        ],
        [
            InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK")),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Indica si aceptas Bizum como forma de pago o no."
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'bizum'
    return CHANGING_BIZUM

def change_car(update, context):
    """Lets driver change their car description"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK"))]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "Escribe la descripción actualizada de tu coche."
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'car'
    return CHANGING_MESSAGE

def change_fee(update, context):
    """Lets driver change their fee"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data=ccd(cdh,"BACK"))]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = ("Escribe el precio del trayecto por pasajero (máximo 1,5€).")
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'fee'
    return CHANGING_MESSAGE

def change_role(update, context):
    """Lets driver change their role"""
    query = update.callback_query
    query.answer()
    role = context.user_data['role']
    keyboard = [[InlineKeyboardButton("Sí", callback_data=ccd(cdh,"YES")),
                 InlineKeyboardButton("No", callback_data=ccd(cdh,"BACK"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"Vas a cambiar tu rol habitual a {role}."
    if role=='Pasajero':
        text += f"\n⚠️ Si haces esto se borrarán todos tus viajes ofertados y"\
                f" tu configuración como conductor.\nSi simplemente quieres pedir"\
                f" coche tú, recuerda que puedes hacerlo aun estando configurado"\
                f" como conductor."
    elif role=='Conductor':
        text += f"\n🚗 Haz esto si piensas empezar a ofertar viajes con tu coche."\
                f" Se te dará acceso a ajustes adicionales para conductores."
    text += f"\n¿Deseas continuar?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'role'
    return CHOOSING_ADVANCED_OPTION

def config_delete_account(update, context):
    """Asks user if they really want to delete their account"""
    query = update.callback_query
    query.answer()
    keyboard = [[InlineKeyboardButton("Sí", callback_data=ccd(cdh,"YES")),
                 InlineKeyboardButton("No", callback_data=ccd(cdh,"BACK"))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = f"⚠️⚠️ Vas a eliminar tu cuenta del bot de BenalUMA. ⚠️⚠️"\
           f"\n Si haces esto, todos tus datos serán eliminados y tendrás que"\
           f" volver a registrarte para poder acceder a todas las funcionalidades"\
           f" de nuevo."
    text += f"\n¿Deseas continuar?"
    query.edit_message_text(text=text, reply_markup=reply_markup)

    context.user_data['config_option'] = 'delete'
    return CHOOSING_ADVANCED_OPTION

def update_user_property(update, context):
    option = context.user_data.pop('config_option')

    text = ""
    if option == 'name':
        set_name(update.effective_chat.id, update.message.text)
        text = f"Nombre de usuario cambiado correctamente."
    elif option == 'car':
        set_car(update.effective_chat.id, update.message.text)
        text = f"Descripción del vehículo actualizada correctamente."
    elif option == 'fee':
        try:
            fee = obtain_float_from_string(update.message.text)
        except:
            fee = -1
        if not (fee>=0 and fee<=MAX_FEE):
            context.user_data['config_option'] = 'fee'
            text = f"Por favor, introduce un número entre 0 y {str(MAX_FEE).replace('.',',')}."
            update.message.reply_text(text)
            return CHANGING_MESSAGE
        else:
            set_fee(update.effective_chat.id, fee)
            text = f"Precio del trayecto actualizado a {str(fee).replace('.',',')}€."

    # Remove possible inline keyboard from previous message
    if 'config_message' in context.user_data:
        sent_message = context.user_data.pop('config_message')
        sent_message.edit_reply_markup(None)

    reply_markup = config_keyboard(update.effective_chat.id)
    text = escape_markdown(text, 2)
    text += f"\n\n Esta es tu configuración actual: \n"
    text += get_formatted_user_config(update.effective_chat.id)
    text += f"\n\nPuedes seguir cambiando ajustes\."
    context.user_data['config_message'] = update.message.reply_text(text,
        reply_markup=reply_markup, parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return CONFIG_SELECT

def update_user_property_callback(update, context):
    query = update.callback_query
    query.answer()

    data = scd(query.data)
    if data[0]!=cdh:
        raise SyntaxError('This callback data does not belong to the update_user_property_callback function.')

    text = ""
    option = context.user_data.pop('config_option')
    if option == 'slots':
        set_slots(update.effective_chat.id, int(data[1]))
        text = f"Número de asientos disponibles cambiado correctamente."
    elif option == 'bizum':
        bizum_flag = True if data[1]=="YES" else False
        set_bizum(update.effective_chat.id, bizum_flag)
        text = f"Preferencia de Bizum modificada correctamente."
    elif option == 'role':
        role = context.user_data.pop('role')
        if role=='Conductor':
            add_driver(update.effective_chat.id, 3, "")
            set_fee(update.effective_chat.id, MAX_FEE)
            modify_request_notification(update.effective_chat.id, 'toBenalmadena')
            modify_request_notification(update.effective_chat.id, 'toUMA')
            text = f"Rol cambiado a conductor correctamente."\
                   f"\n\nSe te aplicado una configuración por defecto. Por favor,"\
                   f" configura correctamente al menos tu número de asientos y"\
                   f" la descripción de tu coche.\n\nAdemás, se te han activado"\
                   f" las notificaciones sobre peticiones de viaje. Puedes cambiar"\
                   f" tus preferencias sobre ello con el comando /notificaciones."
        elif role=='Pasajero':
            delete_driver_notify(update, context, update.effective_chat.id)
            modify_offer_notification(update.effective_chat.id, 'toBenalmadena')
            modify_offer_notification(update.effective_chat.id, 'toUMA')
            text = f"Rol cambiado a pasajero correctamente."
            text += f"\n\nSe te han activado las notificaciones sobre ofertas de"\
                    f" viajes. También se han desactivado para nuevas peticiones,"\
                    f" que no están disponibles para pasajeros. Puedes cambiar"\
                    f" esta configuración con el comando /notificaciones."
    elif option == 'delete':
        delete_user_notify(update, context, update.effective_chat.id)
        text = f"Tu cuenta se ha eliminado correctamente. \n¡Que te vaya bien! 🖖"
        query.edit_message_text(text)
        debug_text = f"El usuario con ID `{update.effective_chat.id}` ha"\
                     f" eliminado su cuenta\."
        debug_group_notify(context, debug_text, telegram.ParseMode.MARKDOWN_V2)
        return ConversationHandler.END

    reply_markup = config_keyboard(update.effective_chat.id)
    text = escape_markdown(text, 2)
    text += f"\n\n Esta es tu configuración actual: \n"
    text += get_formatted_user_config(update.effective_chat.id)
    text += f"\n\nPuedes seguir cambiando ajustes\."
    query.edit_message_text(text, reply_markup=reply_markup,
                            parse_mode=telegram.ParseMode.MARKDOWN_V2)
    return CONFIG_SELECT

def config_end(update, context):
    """Ends configuration conversation."""
    query = update.callback_query
    query.answer()
    if 'config_message' in context.user_data:
        context.user_data.pop('config_message')
    if 'config_option' in context.user_data:
        context.user_data.pop('config_option')
    if 'role' in context.user_data:
        context.user_data.pop('role')
    query.edit_message_text(text="Asistente de configuración de cuenta terminado.")
    return ConversationHandler.END

def add_handlers(dispatcher):
    # Create conversation handler for user configuration
    config_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('config', config)],
        states={
            CONFIG_SELECT: [
                CallbackQueryHandler(change_name, pattern=f"^{ccd(cdh,'NAME')}$"),
                CallbackQueryHandler(config_slots, pattern=f"^{ccd(cdh,'SLOTS')}$"),
                CallbackQueryHandler(config_bizum, pattern=f"^{ccd(cdh,'BIZUM')}$"),
                CallbackQueryHandler(change_car, pattern=f"^{ccd(cdh,'CAR')}$"),
                CallbackQueryHandler(change_fee, pattern=f"^{ccd(cdh,'FEE')}$"),
                CallbackQueryHandler(config_end, pattern=f"^{ccd(cdh,'END')}$"),
                CallbackQueryHandler(config_select_advanced, pattern=f"^{ccd(cdh,'ADVANCED')}$"),
            ],
            CONFIG_SELECT_ADVANCED: [
                CallbackQueryHandler(change_role, pattern=f"^{ccd(cdh,'ROLE')}$"),
                CallbackQueryHandler(config_delete_account, pattern=f"^{ccd(cdh,'DELETE_ACCOUNT')}$"),
            ],
            CHANGING_MESSAGE: [
                MessageHandler(Filters.text & ~Filters.command, update_user_property),
            ],
            CHANGING_SLOTS: [
                CallbackQueryHandler(update_user_property_callback, pattern=f"^{ccd(cdh,'(1|2|3|4|5|6)')}$")
            ],
            CHANGING_BIZUM: [
                CallbackQueryHandler(update_user_property_callback, pattern=f"^{ccd(cdh,'(YES|NO)')}$")
            ],
            CHOOSING_ADVANCED_OPTION: [
                CallbackQueryHandler(update_user_property_callback, pattern=f"^{ccd(cdh,'YES')}$")
            ]
        },
        fallbacks=[CallbackQueryHandler(config_restart, pattern=f"^{ccd(cdh,'BACK')}$"),
                   CommandHandler('config', config)],
    )

    dispatcher.add_handler(config_conv_handler)
