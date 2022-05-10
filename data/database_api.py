import firebase_admin
from firebase_admin import db
import json
from datetime import datetime
from utils.common import week_isoformats
from collections import OrderedDict

# General

def add_user(chat_id, username):
    """Adds a new user to the database given its chat_id.

    Parameters
    ----------
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
        The chat_id to delete.

    Returns
    -------
    None

    """

    delete_all_trips_by_driver(chat_id)
    db.reference(f"/Drivers/{str(chat_id)}").delete()
    # Note: All passengers from deteled trips should be noticed about the deletion
    # Maybe do that outside the DB functions, as DB does not need to know about that

def get_slots(chat_id):
    """Gets the number of slots of a driver.

    Parameters
    ----------
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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
    chat_id : int or string
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

def add_trip(direction, chat_id, date, time, slots = None, fee = None):
    """Creates new trip with given information.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    chat_id : int or string
        The chat_id of the driver.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'
    time : string
        Departure time with ISO format 'HH:MM'
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

    if slots != None:
        trip_dict['Slots'] = slots

    if fee != None:
        trip_dict['Fee'] = fee

    key = ref.push(trip_dict).key

    # Now add the key to the driver's offers section
    ref = db.reference(f"/Drivers/{chat_id}/Offers/{direction}/{date}/{key}")
    ref.set(True)

    return key

def delete_trip(direction, date, key):
    """Deletes a trip.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    None

    """
    chat_id = get_trip_chat_id(direction, date, key)
    db.reference(f"/Trips/{direction}/{date}/{key}").delete()
    db.reference(f"/Drivers/{chat_id}/Offers/{direction}/{date}/{key}").delete()

    # Remove passengers if any
    for passenger_id in get_trip_passengers(direction, date, key):
        remove_passenger(passenger_id, direction, date, key)

def get_trip(direction, date, key):
    """Gets a dictionary with the given trip info.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    dict
        Trip information.

    """
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.get()

def get_trip_time(direction, date, key):
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.child('Time').get()

def get_trip_chat_id(direction, date, key):
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.child('Chat ID').get()

def get_trip_slots(direction, date, key):
    ref = db.reference(f"/Trips/{direction}/{date}/{key}")
    return ref.child('Slots').get()

def get_trips_by_date_range(direction, date, time_start=None, time_end=None):
    """Gets a dictionary with the offered trips for a given date and,
    optionally, time range

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    time_start : string
        Sooner departure time to search for, with ISO format 'HH:MM'.
    time_end : string
        Latest departure time to search for, with ISO format 'HH:MM'.

    Returns
    -------
    dict
        Dictionary with found trips. It has the following format:
        {'trip_unique_key_1': <dict with trip info 1>,
         'trip_unique_key_2': <dict with trip info 2>,
         ...}

    """
    ref = db.reference(f"/Trips/{direction}/{date}/")
    query = ref.order_by_child("Time")

    if time_start:
        query = query.start_at(time_start)
    if time_end:
        query = query.end_at(time_end)

    return query.get()

def get_trips_by_driver(chat_id, date_start=None, date_end=None, order_by_date=False):
    """Return a dictionary with all the planned trips for a given driver
    between the given dates.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the driver.
    date_start : string
        Range's start date with ISO format 'YYYY-mm-dd'. Optional
    date_end : string
        Range's stop date with ISO format 'YYYY-mm-dd'. Optional
    order_by_date : boolean
        Flag which indicates whether to order the trips by date instead of by
        direction. If True, each trip contains a 'Direction' field. False by default.

    Returns
    -------
    dict
        Dictionary with the planned trips.

    """
    ref = db.reference(f"/Drivers/{chat_id}/Offers")
    trips_dict = dict()

    for dir in ['toBenalmadena', 'toUMA']:
        query = ref.child(dir).order_by_key()
        if date_start:
            query = query.start_at(date_start)
        if date_end:
            query = query.end_at(date_end)

        trip_keys_dict = query.get()
        if trip_keys_dict:
            dir_trips = dict()
            for date in trip_keys_dict:
                date_trips = dict()
                for key in trip_keys_dict[date]:
                    date_trips[key] = get_trip(dir, date, key)
                if date_trips:
                    dir_trips[date] = OrderedDict(
                            sorted(date_trips.items(), key=lambda x: x[1]['Time']))
            if dir_trips:
                trips_dict[dir] = dir_trips

    if trips_dict:
        if order_by_date:
            trips_dict_by_date = dict()
            dates = set()
            # First narrow down the dates to process
            for dir in trips_dict:
                dates = dates.union(set(trips_dict[dir]))
            # We want to present the trips by date
            for date in sorted(dates):
                date_trips = dict()
                for dir in trips_dict:
                    if date in trips_dict[dir]:
                        # Save the direction of each trip in an specific field
                        for key in trips_dict[dir][date]:
                            trips_dict[dir][date][key]['Direction'] = dir
                        date_trips.update(trips_dict[dir][date])
                # Order dict by time if it exists
                if date_trips:
                    trips_dict_by_date[date] = OrderedDict(
                            sorted(date_trips.items(), key=lambda x: x[1]['Time']))
            return trips_dict_by_date
        return trips_dict
    return

    # # OLD IMPLEMENTATION
    # ref = db.reference("/Trips/")
    # all_trips = dict()
    # for dir in ['toBenalmadena', 'toUMA']:
    #     dir_trips = dict()
    #     ref2 = ref.child(dir)
    #
    #     for date in week_isoformats():
    #         db_query = ref2.child(date).order_by_child('Chat ID')
    #         day_trips_dict = db_query.equal_to(chat_id).get()
    #         if day_trips_dict:
    #             dir_trips[date] = day_trips_dict
    #
    #     if dir_trips:
    #         all_trips[dir] = dir_trips
    #
    # if all_trips:
    #     return all_trips
    #
    # return

def get_trips_by_passenger(chat_id, date_start=None, date_end=None, order_by_date=False):
    """Return a dictionary with all the reserved trips for a given user between
    the given dates.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.
    date_start : string
        Range's start date with ISO format 'YYYY-mm-dd'. Optional
    date_end : string
        Range's stop date with ISO format 'YYYY-mm-dd'. Optional
    order_by_date : boolean
        Flag which indicates whether to order the trips by date instead of by
        direction. If True, each trip contains a 'Direction' field. False by default.

    Returns
    -------
    dict
        Dictionary with the reserved trips.

    """
    ref = db.reference(f"/Passengers/{chat_id}")
    trips_dict = dict()

    for dir in ['toBenalmadena', 'toUMA']:
        query = ref.child(dir).order_by_key()
        if date_start:
            query = query.start_at(date_start)
        if date_end:
            query = query.end_at(date_end)

        trip_keys_dict = query.get()
        if trip_keys_dict:
            dir_trips = dict()
            for date in trip_keys_dict:
                date_trips = dict()
                for key in trip_keys_dict[date]:
                    date_trips[key] = get_trip(dir, date, key)
                if date_trips:
                    dir_trips[date] = OrderedDict(sorted(date_trips.items(), key=lambda x: x[1]['Time']))
            if dir_trips:
                trips_dict[dir] = dir_trips

    if trips_dict:
        if order_by_date:
            trips_dict_by_date = dict()
            dates = set()
            # First narrow down the dates to process
            for dir in trips_dict:
                dates = dates.union(set(trips_dict[dir]))
            # We want to present the trips by date
            for date in dates:
                date_trips = dict()
                for dir in trips_dict:
                    if date in trips_dict[dir]:
                        # Save the direction of each trip in an specific field
                        for key in trips_dict[dir][date]:
                            trips_dict[dir][date][key]['Direction'] = dir
                        date_trips.update(trips_dict[dir][date])
                # Order dict by time if it exists
                if date_trips:
                    trips_dict_by_date[date] = OrderedDict(
                            sorted(date_trips.items(), key=lambda x: x[1]['Time']))
            return trips_dict_by_date
        return trips_dict
    return

def delete_all_trips_by_driver(chat_id):
    """Deletes all the planned trips for a given driver.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the driver.

    Returns
    -------
    None

    """
    ref = db.reference(f"/Drivers/{chat_id}/Offers")
    trips_dict = ref.get()
    if trips_dict:
        for dir in trips_dict:
            for date in trips_dict[dir]:
                for trip_key in trips_dict[dir][date]:
                    delete_trip(dir, date, trip_key)

def add_passenger(chat_id, direction, date, key):
    """Add passenger given by chat_id to the specified trip.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user to add as passenger.
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    Boolean
        True if the user was added correctly.

    """
    ref = db.reference(f"/Trips/{direction}/{date}/{key}/Passengers")
    passengers_dict = ref.get()

    if passengers_dict:
        ref.update({chat_id: True})
    else:
        passengers_dict = {chat_id: True}
        ref.set(passengers_dict)

    # Now add it to the passenger's own list of reserved trips
    ref = db.reference(f"/Passengers/{chat_id}/{direction}/{date}/{key}")
    ref.set(True)

    return True

def is_passenger(chat_id, direction, date, key):
    """Checks whether user is already a passenger in the trip.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user to remove from passengers list.
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    boolean
        True if user is passenger already, False otherwise.

    """
    ref = db.reference(f"/Passengers/{chat_id}/{direction}/{date}/{key}")
    if ref.get():
        return True
    else:
        return False

def get_trip_passengers(direction, date, key):
    """Returns the list of confirmed passengers in a trip.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    list
        List with the chat IDs of the passengers, if any

    """
    ref = db.reference(f"/Trips/{direction}/{date}/{key}/Passengers")
    passengers_dict = ref.get()
    if passengers_dict:
        return list(passengers_dict)
    else:
        return list()

def get_number_of_passengers(direction, date, key):
    """Returns the number of confirmed passengers in a trip.

    Parameters
    ----------
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    integer
        Number of passengers in the trip.

    """
    ref = db.reference(f"/Trips/{direction}/{date}/{key}/Passengers")
    passengers_dict = ref.get()
    if passengers_dict:
        return len(passengers_dict)
    else:
        return 0

def remove_passenger(chat_id, direction, date, key):
    """Remove passenger given by chat_id to the specified trip.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user to remove from passengers list.
    direction : string
        Direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the trip.

    Returns
    -------
    Boolean
        True if the user was removed correctly.
        False if the user was not a passenger in this trip.

    """
    ref = db.reference(f"/Passengers/{chat_id}/{direction}/{date}/{key}")
    if ref.get():
        # Delete it from the passenger's own list of reserved trips
        ref.delete()
        # Now delete passenger from passenger list in trip info
        ref = db.reference(f"/Trips/{direction}/{date}/{key}/Passengers")
        ref.child(str(chat_id)).delete()
    else:
        return False

    return True
