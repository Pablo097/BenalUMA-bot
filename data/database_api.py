import firebase_admin
from firebase_admin import db
import json

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
    ref = db.reference('/Users/'+str(chat_id))
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

    return db.reference('/Users/'+str(chat_id)+'/Name').get()

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

    db.reference('/Users/'+str(chat_id)).delete()
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

    ref = db.reference('/Drivers/'+str(chat_id))
    ref.set({"Slots": str(slots)})
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

    db.reference('/Drivers/'+str(chat_id)).delete()

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

    ref = db.reference('/Drivers/'+str(chat_id))
    return int(ref.child('Slots').get())

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

    ref = db.reference('/Drivers/'+str(chat_id))
    return ref.child('Car').get()
