import firebase_admin
from firebase_admin import db
import json
from datetime import datetime

# General

def add_user(chat_id, username):
    """Adds a new user to the database given its chat_id.

    Parameters
    ----------
    chat_id : int
        The chat_id of the user.
    username : str
        The given username.

    Returns
    -------
    None

    """
    ref = db.reference(f"/Users/{str(chat_id)}")
    ref.set({"Name": username})

def is_registered(chat_id):
    """Checks whether a user is already registered in the database.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    boolean
        True if it is already registered, False otherwise.

    """
    ref = db.reference('/Users')
    return ref.child(str(chat_id)).get() != None

def get_name(chat_id):
    """Gets the username given its chat_id.

    Parameters
    ----------
    chat_id : int
        The chat_id to check

    Returns
    -------
    str
        The username.

    """

    return db.reference(f"/Users/{str(chat_id)}/Name").get()

def set_name(chat_id, name):
    """Sets the username given its chat_id.

    Parameters
    ----------
    chat_id : int
        The chat_id to check
    name: string
        The name for the user

    Returns
    -------
    None

    """

    ref = db.reference(f"/Users/{str(chat_id)}")
    ref.update({'Name': name})

def delete_user(chat_id):
    """Deletes user from database.

    Parameters
    ----------
    chat_id : int
        The chat_id to delete.

    Returns
    -------
    None

    """

    db.reference(f"/Users/{str(chat_id)}").delete()
    if is_driver(chat_id):
        delete_driver(chat_id)


# Drivers

def add_driver(chat_id, slots, car):
    """Adds a currently registered user to the drivers list.

    Parameters
    ----------
    chat_id : int
        The chat_id to add.
    slots : int
        Number of available seats, excluding the driver.
    car : str
        Description of the car.

    Returns
    -------
    None

    """

    ref = db.reference(f"/Drivers/{str(chat_id)}")
    ref.set({"Slots": slots})
    ref.update({"Car": car})

def is_driver(chat_id):
    """Checks whether the user given by chat_id is a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    boolean
        True if it is a driver, False otherwise.

    """

    ref = db.reference('/Drivers')
    return ref.child(str(chat_id)).get() != None

def delete_driver(chat_id):
    """Deletes user from the drivers list.

    Parameters
    ----------
    chat_id : int
        The chat_id to delete.

    Returns
    -------
    None

    """

    db.reference(f"/Drivers/{str(chat_id)}").delete()
    # TODO: Delete all possible planned trips
    # (inside delete_trip function, alert possible passengers that the
    # trip has been cancelled)

def get_slots(chat_id):
    """Gets the number of slots of a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    int
        The number of available slots.

    """

    ref = db.reference(f"/Drivers/{str(chat_id)}")
    return int(ref.child('Slots').get())

def set_slots(chat_id, slots):
    """Sets the number of slots of a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id of the driver.
    slots : int
        Number of available seats, excluding the driver.

    Returns
    -------
    None

    """

    db.reference(f"/Drivers/{str(chat_id)}").update({"Slots": slots})

def get_car(chat_id):
    """Gets the car description of a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    str
        Description of the car.

    """

    ref = db.reference(f"/Drivers/{str(chat_id)}")
    return ref.child('Car').get()

def set_car(chat_id, car):
    """Sets the car description of a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id of the driver.
    car : str
        Description of the car.

    Returns
    -------
    None

    """

    db.reference(f"/Drivers/{str(chat_id)}").update({"Car": car})

def get_fee(chat_id):
    """Gets the per-user payment quantity for a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    float
        Driver's fee.

    """

    ref = db.reference(f"/Drivers/{str(chat_id)}")
    fee = ref.child('Fee').get()
    if fee != None:
        return float(fee)
    else:
        return None

def set_fee(chat_id, fee):
    """Sets the per-user payment quantity for a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id of the driver.
    fee : float
        The driver's fee.

    Returns
    -------
    None

    """

    db.reference(f"/Drivers/{str(chat_id)}").update({"Fee": fee})

def get_bizum(chat_id):
    """Gets the Bizum preference a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id to check.

    Returns
    -------
    boolean
        True if the driver accepts Bizum, False otherwise.

    """

    ref = db.reference(f"/Drivers/{str(chat_id)}")
    bizum = ref.child('Bizum').get()
    if bizum == 'Yes':
        return True
    elif bizum == 'No':
        return False

    return None

def set_bizum(chat_id, bizum_pref):
    """Sets the Bizum preference a driver.

    Parameters
    ----------
    chat_id : int
        The chat_id of the driver.
    bizum_pref : boolean
        True for indicating that Bizum is accepted, False otherwise.

    Returns
    -------
    None

    """

    ref = db.reference(f"/Drivers/{str(chat_id)}")
    if bizum_pref:
        ref.update({"Bizum": "Yes"})
    else:
        ref.update({"Bizum": "No"})


# Trips

def add_trip(direction, chat_id, date, time, time_window = 0,
             slots = None, fee = None):
    """Creates new trip with given information.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    chat_id : int
        The chat_id of the driver.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'
    time : string
        Departure time with ISO format 'HH:MM'
    time_window : int
        Determines how flexible is the departure time as the number of
        minutes from it.
    slots : int
        Optional. Number of available slots for this specific trip.
    fee : float
        Optional. The per-user payment quantity.

    Returns
    -------
    string
        Key of the newly created DB reference.

    """
    ref = db.reference(f"/Trips/{direction}")
    # date_string = departure_date.strftime('%Y-%m-%d')
    ref = ref.child(date)

    # time_string = departure_date.strftime('%H:%M')
    trip_dict = {'Chat ID': chat_id,
                 'Time': time}

    if time_window>0:
        trip_dict['Time Window'] = time_window

    if slots != None:
        trip_dict['Slots'] = slots

    if fee != None:
        trip_dict['Fee'] = fee

    return ref.push(trip_dict).key

def get_trip(direction, date, key):
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.get()

def get_trip_time(direction, date, key):
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.child('Time').get()

def get_trip_chat_id(direction, date, key):
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.child('Chat ID').get()
