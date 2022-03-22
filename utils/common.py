import logging
from data.database_api import get_name, is_driver, get_slots, get_car, get_fee, get_bizum

MAX_FEE = 1.5

emoji_numbers = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

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
    string = "💬 *Nombre*: `" + get_name(chat_id) + "`"
    role = 'Conductor' if is_driver(chat_id) else 'Pasajero'
    string += "\n🧍 *Rol*: `" + role + "`"

    if role == 'Conductor':
        string += "\n💺 *Asientos disponibles*: `" + str(get_slots(chat_id)) + "`"
        string += "\n🚘 *Descripción vehículo*: `" + get_car(chat_id) + "`"
        fee = get_fee(chat_id)
        if fee != None:
            string += "\n🪙 *Pago por trayecto*: `" + str(fee).replace('.',',') + "€`"
        bizum = get_bizum(chat_id)
        if bizum == True:
            string += "\n💸 `Aceptas Bizum`"
        elif bizum == False:
            string += "\n💸🚫 `NO aceptas Bizum`"

    return string
