import firebase_admin
from firebase_admin import db
import json
from datetime import datetime
from utils.common import week_isoformats, weekdays_en
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

def get_all_chat_ids():
    """Gets a list with all registered users' chat IDs

    Returns
    -------
    list(str)
        List with registered chat IDs. 

    """
    users_dict = db.reference("/Users").get()
    if users_dict:
        return list(users_dict)
    else:
        return list()

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

def get_tg_username(chat_id):
    """Gets the Telegram username given its chat_id.

    Parameters
    ----------
    chat_id : int or string
        The chat_id to check

    Returns
    -------
    str
        The Telegram username starting with '@'.

    """

    return db.reference(f"/Users/{str(chat_id)}/Username").get()

def set_tg_username(chat_id, username):
    """Sets the Telegram username given its chat_id.

    Parameters
    ----------
    chat_id : int or string
        The chat_id to check
    username: string
        The Telegram username of the user (it must start with '@')

    Returns
    -------
    None

    """
    if username[0]!='@':
        username = f"@{username}"
    ref = db.reference(f"/Users/{str(chat_id)}")
    ref.update({'Username': username})

def get_chat_id_from_tg_username(username):
    """Gets the chat_id from the given Telegram username.

    Parameters
    ----------
    username: string
        The Telegram username of the user (it must start with '@')

    Returns
    -------
    str
        The user chat_id, if it is associated with any Telegram username
        in the database, an empty string otherwise.

    """
    if username[0]!='@':
        username = f"@{username}"
    user_dict = db.reference("/Users").order_by_child('Username').equal_to(username).get()
    if user_dict:
        for user_id in user_dict:
            return user_id
    else:
        return ''

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
    # Delete possible offers notifications configuration
    notif_dict = get_offer_notification_by_user(chat_id)
    if notif_dict:
        for dir in notif_dict:
            delete_offer_notification(chat_id, dir)
    # Delete published requests
    delete_all_requests_by_user(chat_id)
    # Delete possible driver-related things
    if is_driver(chat_id):
        delete_driver(chat_id)
    # Finally, completely delete user
    db.reference(f"/Users/{str(chat_id)}").delete()

def ban_user(chat_id):
    """Bans user from bot.

    Parameters
    ----------
    chat_id : int or string
        The chat_id to ban.

    Returns
    -------
    None

    """
    # Delete user if registered
    if is_registered(chat_id):
        delete_user(chat_id)
    # Put user ID in banned list
    db.reference(f"/Banned/{str(chat_id)}").set(True)

def is_banned(chat_id):
    """Checks whether user is banned from bot.

    Parameters
    ----------
    chat_id : int or string
        The chat_id to check.

    Returns
    -------
    Boolean
        True if it is banned, False otherwise.

    """
    return True if db.reference(f"/Banned/{str(chat_id)}").get()==True else False

def unban_user(chat_id):
    """Unbans user from bot.

    Parameters
    ----------
    chat_id : int or string
        The chat_id to unban.

    Returns
    -------
    None

    """
    if is_banned(chat_id):
        db.reference(f"/Banned/{str(chat_id)}").delete()


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
    # Delete possible request notifications configuration
    notif_dict = get_request_notification_by_user(chat_id)
    if notif_dict:
        for dir in notif_dict:
            delete_request_notification(chat_id, dir)
    # Delete published trips
    delete_all_trips_by_driver(chat_id)
    # Finally, delete driver
    db.reference(f"/Drivers/{str(chat_id)}").delete()

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


# Requests

def add_request(direction, chat_id, date, time):
    """Creates new request with given information.

    Parameters
    ----------
    direction : string
        Required direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    chat_id : int or string
        The chat_id of the requester.
    date : string
        Required departure date with ISO format 'YYYY-mm-dd'
    time : string
        Desired departure time with ISO format 'HH:MM'

    Returns
    -------
    string
        Key of the newly created DB reference.

    """
    ref = db.reference(f"/Requests/{direction}/{date}")

    req_dict = {'Chat ID': chat_id,
                 'Time': time}

    key = ref.push(req_dict).key

    # Now add the key to the user's requests section
    ref = db.reference(f"/Users/{chat_id}/Requests/{direction}/{date}/{key}")
    ref.set(True)

    return key

def delete_request(direction, date, key):
    """Deletes a request.

    Parameters
    ----------
    direction : string
        Required direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Required departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the request.

    Returns
    -------
    None

    """
    chat_id = get_request_chat_id(direction, date, key)
    db.reference(f"/Requests/{direction}/{date}/{key}").delete()
    db.reference(f"/Users/{chat_id}/Requests/{direction}/{date}/{key}").delete()

def get_request(direction, date, key):
    """Gets a dictionary with the given request info.

    Parameters
    ----------
    direction : string
        Required direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Required departure date with ISO format 'YYYY-mm-dd'.
    key : string
        Unique key identifying the request.

    Returns
    -------
    dict
        Request information.

    """
    ref = db.reference(f"/Requests/{direction}/{date}/{key}")
    return ref.get()

def get_request_chat_id(direction, date, key):
    ref = db.reference(f"/Requests/{direction}/{date}/{key}")
    return ref.child('Chat ID').get()

def get_request_time(direction, date, key):
    ref = db.reference(f"/Requests/{direction}/{date}/{key}")
    return ref.child('Time').get()

def get_requests_by_date_range(direction, date, time_start=None, time_end=None):
    """Gets a dictionary with the trip requests for a given date and,
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
        Dictionary with found requests. It has the following format:
        {'request_unique_key_1': <dict with request info 1>,
         'request_unique_key_2': <dict with request info 2>,
         ...}

    """
    ref = db.reference(f"/Requests/{direction}/{date}/")
    query = ref.order_by_child("Time")

    if time_start:
        query = query.start_at(time_start)
    if time_end:
        query = query.end_at(time_end)

    return query.get()

def get_requests_by_user(chat_id, date_start=None, date_end=None, order_by_date=False):
    """Return a dictionary with all the trip requests for a given user
    between the given dates.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.
    date_start : string
        Range's start date with ISO format 'YYYY-mm-dd'. Optional
    date_end : string
        Range's stop date with ISO format 'YYYY-mm-dd'. Optional
    order_by_date : boolean
        Flag which indicates whether to order the requests by date instead of by
        direction. If True, each request contains a 'Direction' field. False by default.

    Returns
    -------
    dict
        Dictionary with the trip requests.

    """
    ref = db.reference(f"/Users/{chat_id}/Requests")
    reqs_dict = dict()

    for dir in ['toBenalmadena', 'toUMA']:
        query = ref.child(dir).order_by_key()
        if date_start:
            query = query.start_at(date_start)
        if date_end:
            query = query.end_at(date_end)

        reqs_keys_dict = query.get()
        if reqs_keys_dict:
            dir_reqs = dict()
            for date in reqs_keys_dict:
                date_reqs = dict()
                for key in reqs_keys_dict[date]:
                    date_reqs[key] = get_request(dir, date, key)
                if date_reqs:
                    dir_reqs[date] = OrderedDict(
                            sorted(date_reqs.items(), key=lambda x: x[1]['Time']))
            if dir_reqs:
                reqs_dict[dir] = dir_reqs

    if reqs_dict:
        if order_by_date:
            reqs_dict_by_date = dict()
            dates = set()
            # First narrow down the dates to process
            for dir in reqs_dict:
                dates = dates.union(set(reqs_dict[dir]))
            # We want to present the requests by date
            for date in sorted(dates):
                date_reqs = dict()
                for dir in reqs_dict:
                    if date in reqs_dict[dir]:
                        # Save the direction of each request in an specific field
                        for key in reqs_dict[dir][date]:
                            reqs_dict[dir][date][key]['Direction'] = dir
                        date_reqs.update(reqs_dict[dir][date])
                # Order dict by time if it exists
                if date_reqs:
                    reqs_dict_by_date[date] = OrderedDict(
                            sorted(date_reqs.items(), key=lambda x: x[1]['Time']))
            return reqs_dict_by_date
        return reqs_dict
    return

def get_requests_by_user_and_date(chat_id, direction, date, time_start=None, time_end=None):
    """Return a dictionary with all the trip requests for a given user in the
    specified direction and date.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.
    direction : string
        Required direction of the trip. Can be 'toBenalmadena' or 'toUMA'.
    date : string
        Required departure date with ISO format 'YYYY-mm-dd'.
    time_start : string
        Sooner departure time to search for, with ISO format 'HH:MM'.
    time_end : string
        Latest departure time to search for, with ISO format 'HH:MM'.

    Returns
    -------
    dict
        Dictionary with the trip requests.

    """
    ref = db.reference(f"/Users/{chat_id}/Requests/{direction}/{date}")

    reqs_dict = dict()
    reqs_keys_dict = ref.get()

    if reqs_keys_dict:
        for key in reqs_keys_dict:
            req_aux = get_request(direction, date, key)
            if time_end>=req_aux['Time']>=time_start:
                reqs_dict[key] = req_aux

    if reqs_dict:
        reqs_dict = OrderedDict(
                sorted(reqs_dict.items(), key=lambda x: x[1]['Time']))
        return reqs_dict
    return

def delete_all_requests_by_user(chat_id):
    """Deletes all the trip requests for a given user.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.

    Returns
    -------
    None

    """
    ref = db.reference(f"/Users/{chat_id}/Requests")
    reqs_dict = ref.get()
    if reqs_dict:
        for dir in reqs_dict:
            for date in reqs_dict[dir]:
                for req_key in reqs_dict[dir][date]:
                    delete_request(dir, date, req_key)

# Notifications

def get_offer_notification_by_user(chat_id, direction=None):
    """Gets a dictionary with the configured offers' notifications for a given
    user and, optionally, a direction

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.
    direction : string
        Optional. Direction of the trip for notifications.
        If set, can be 'toBenalmadena' or 'toUMA'.

    Returns
    -------
    dict
        Ordered-by-weekday Dictionary with the configured notifications.
        If no notifications are set, it will be empty.

    """
    ref = db.reference(f"/Users/{chat_id}/Offer Notifications")

    wd_aux = ['All days'] + weekdays_en

    if not direction:
        notif_dict = ref.get()
        if not notif_dict:
            return dict()
        for dir in notif_dict:
            notif_dict[dir] = dict(sorted(notif_dict[dir].items(), key=lambda x: wd_aux.index(x[0])))
    else:
        notif_dict = ref.child(direction).get()
        if not notif_dict:
            return dict()
        notif_dict = dict(sorted(notif_dict.items(), key=lambda x: wd_aux.index(x[0])))

    return notif_dict

def get_request_notification_by_user(chat_id, direction=None):
    """Gets a dictionary with the configured requests' notifications for a given
    user and, optionally, a direction

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user.
    direction : string
        Optional. Direction of the trip for notifications.
        If set, can be 'toBenalmadena' or 'toUMA'.

    Returns
    -------
    dict
        Ordered-by-weekday Dictionary with the configured notifications.
        If no notifications are set, it will be empty.

    """
    ref = db.reference(f"/Drivers/{chat_id}/Request Notifications")

    wd_aux = ['All days'] + weekdays_en

    if not direction:
        notif_dict = ref.get()
        if not notif_dict:
            return dict()
        for dir in notif_dict:
            notif_dict[dir] = dict(sorted(notif_dict[dir].items(), key=lambda x: wd_aux.index(x[0])))
    else:
        notif_dict = ref.child(direction).get()
        if not notif_dict:
            return dict()
        notif_dict = dict(sorted(notif_dict.items(), key=lambda x: wd_aux.index(x[0])))

    return notif_dict

def get_users_for_offer_notification(direction, weekday, time):
    """Get list of all interested users to notify given a direction, weekday
    and time for a trip offer

    Parameters
    ----------
    direction : string
        Direction of the offered trip. Can be 'toBenalmadena' or 'toUMA'.
    weekday : string
        Week day of the offered trip. Must be one from ('Monday', ..., 'Sunday').
    time : string
        Departure time with ISO format 'HH:MM'

    Returns
    -------
    list
        chat_id's of the interested users.

    """
    ref = db.reference(f"/Notifications/Offers/{direction}")

    hour = int(time[:2])
    minutes = int(time[-2:])
    users = set()

    # Add users that get notified for every day and every hour
    if aux:=ref.child('All days').child('All hours').get():
        users |= set(aux)
    # Add users that get notified for THIS week day and every hour
    if aux:=ref.child(weekday).child('All hours').get():
        users |= set(aux)
    # Add users that get notified for every day and THIS hour
    if aux:=ref.child('All days').child(str(hour)).get():
        users |= set(aux)
    # Add users that get notified for THIS week day and THIS hour
    if aux:=ref.child(weekday).child(str(hour)).get():
        users |= set(aux)
    # If hour is o'clock, notify also the users just in the previous configured hour
    if minutes == 0 and hour>0:
        # Add users that get notified for every day and THIS hour
        if aux:=ref.child('All days').child(str(hour-1)).get():
            users |= set(aux)
        # Add users that get notified for THIS week day and THIS hour
        if aux:=ref.child(weekday).child(str(hour-1)).get():
            users |= set(aux)

    if users:
        return list(users)
    else:
        return list()

def get_users_for_request_notification(direction, weekday):
    """Get list of all interested users to notify given a direction and weekday
    for a trip request

    Parameters
    ----------
    direction : string
        Direction of the requested trip. Can be 'toBenalmadena' or 'toUMA'.
    weekday : string
        Week day of the requested trip. Must be one from ('Monday', ..., 'Sunday').

    Returns
    -------
    list
        chat_id's of the interested users.

    """
    ref = db.reference(f"/Notifications/Requests/{direction}")

    users = set()

    # Add users that get notified for every day
    if aux:=ref.child('All days').get():
        users |= set(aux)
    # Add users that get notified for THIS week day
    if aux:=ref.child(weekday).get():
        users |= set(aux)

    if users:
        return list(users)
    else:
        return list()

def modify_offer_notification(chat_id, direction, weekday=None, time_range=None):
    """Modifies the offers' notifications for a given user, direction and,
    optionally, week day and time range. It overwrites the previous configuration
    for this specific combination, if it exists.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user for whom to modify the notifications.
    direction : string
        Direction of the trip for notifications. Can be 'toBenalmadena' or 'toUMA'.
    weekday : string
        Optional. Week day for the notifications.
        If set, must be one from ('Monday', ..., 'Sunday').
        If not passed, the notifications will be activated for all days.
    time_range : list[2x int]
        List of two integers indicating the start and end hours for the
        departure time of the offered trips to be notified about them.

    Returns
    -------
    boolean
        True if the modification was successfull, False if the notification for
        the chosen combination was already the same.

    """
    ref = db.reference(f"/Users/{chat_id}/Offer Notifications/{direction}")
    notif_dict = ref.get()
    is_configured = False

    # Update the user's dictionary
    if weekday:
        if weekday not in weekdays_en:
            raise ValueError("weekday doesn't have a valid value")
        if notif_dict!=None and weekday in notif_dict:
            is_configured = True
        else:
            # If 'All days' was previously set, delete it
            delete_offer_notification(chat_id, direction, 'All days')
        # Set required reference
        ref = ref.child(weekday)
    else:
        if notif_dict!=None and 'All days' in notif_dict:
            is_configured = True
        else:
            delete_offer_notification(chat_id, direction)
        ref = ref.child('All days')

    # Configure user's weekday offers notifications dictionary
    if time_range:
        if time_range[0]>time_range[1] or time_range[0]<0 or time_range[1]>24:
            raise ValueError("time_range list doesn't have valid values")
        ref.set({'Start': time_range[0], 'End': time_range[1]})
    else:
        ref.set(True)

    weekday = 'All days' if not weekday else weekday
    # Now update the general users notifications dictionary
    ref2 = db.reference(f"/Notifications/Offers/{direction}/{weekday}")

    # If this weekday option was already configured, we only modify it
    if is_configured:
        if notif_dict[weekday] == True:
            if not time_range:
                return False    # The configuration is the same!
            else:
                ref2.child('All hours').child(str(chat_id)).delete()
                hours = list(range(time_range[0], time_range[1]))
                for hour in hours:
                    ref2.child(str(hour)).child(str(chat_id)).set(True)
        else:
            old_hours = list(range(notif_dict[weekday]['Start'], notif_dict[weekday]['End']))
            if not time_range:
                hours_to_delete = old_hours
                ref2.child('All hours').child(str(chat_id)).set(True)
            else:
                hours = list(range(time_range[0], time_range[1]))
                if old_hours==hours:
                    return False    # The configuration is the same!
                hours_to_delete = list(set(old_hours)-set(hours))
                hours = list(set(hours)-set(old_hours))
                for hour in hours:
                    ref2.child(str(hour)).child(str(chat_id)).set(True)
            for hour in hours_to_delete:
                ref2.child(str(hour)).child(str(chat_id)).delete()
    # If this weekday didn't have a previous configuration, create it
    else:
        if not time_range:
            ref2.child('All hours').child(str(chat_id)).set(True)
        else:
            for hour in range(time_range[0], time_range[1]):
                ref2.child(str(hour)).child(str(chat_id)).set(True)

    return True

def modify_request_notification(chat_id, direction, weekday=None):
    """Modifies the requests' notifications for a given user, direction and,
    optionally, week day. It overwrites the previous configuration
    for this specific combination, if it exists.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user for whom to modify the notifications.
    direction : string
        Direction of the trip for notifications. Can be 'toBenalmadena' or 'toUMA'.
    weekday : string
        Optional. Week day for the notifications.
        If set, must be one from ('Monday', ..., 'Sunday').
        If not passed, the notifications will be activated for all days.

    Returns
    -------
    boolean
        True if the modification was successfull, False if the notification for
        the chosen combination was already the same.

    """
    ref = db.reference(f"/Drivers/{chat_id}/Request Notifications/{direction}")
    notif_dict = ref.get()
    is_configured = False

    # Update the user's dictionary
    if weekday:
        if weekday not in weekdays_en:
            raise ValueError("weekday doesn't have a valid value")
        if notif_dict!=None and weekday in notif_dict:
            return False
        else:
            # If 'All days' was previously set, delete it
            delete_request_notification(chat_id, direction, 'All days')
        # Set required reference
        ref = ref.child(weekday)
    else:
        if notif_dict!=None and 'All days' in notif_dict:
            return False
        else:
            delete_request_notification(chat_id, direction)
        ref = ref.child('All days')

    # Enable notifications for this weekday
    ref.set(True)

    weekday = 'All days' if not weekday else weekday
    # Now update the general users notifications dictionary
    ref2 = db.reference(f"/Notifications/Requests/{direction}/{weekday}")
    ref2.child(str(chat_id)).set(True)

    return True

def delete_offer_notification(chat_id, direction, weekday=None):
    """Deletes the offers' notifications for a given user, direction and week
    day.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user for whom to delete the notifications.
    direction : string
        Direction of the trip for notifications. Can be 'toBenalmadena' or 'toUMA'.
    weekday : string
        Optional. Week day for the notifications.
        Must be 'All days' or one from ('Monday', ..., 'Sunday').
        If not passed, the deletion will be done for the whole direction.

    Returns
    -------
    boolean
        True if the deletion was successfull, False if the notification for the
        chosen direction and weekday was not already configured.

    """
    def remove_general_weekday_notif(chat_id, direction, weekday, notif_config):
        """Auxiliary function for other notification database functions"""
        # General users' notifications dictionary
        ref2 = db.reference(f"/Notifications/Offers/{direction}/{weekday}")
        # Delete from general users' notifications dictionary
        if notif_config == True:   # Notifications set for every hour
            ref2.child('All hours').child(str(chat_id)).delete()
        else:
            start_hour = int(notif_config['Start'])
            end_hour = int(notif_config['End'])
            for hour in range(start_hour, end_hour):
                ref2.child(str(hour)).child(str(chat_id)).delete()

    # User's offers notifications dictionary
    ref = db.reference(f"/Users/{chat_id}/Offer Notifications/{direction}")

    if weekday:
        if weekday not in weekdays_en+['All days']:
            raise ValueError("weekday doesn't have a valid value")
        weekday_notif_dict = ref.child(weekday).get()
        # Check if notification setting exists for this week day
        if weekday_notif_dict==None:
            return False

        # Delete from user's dictionary
        ref.child(weekday).delete()
        # Delete from general users' notifications dictionary
        remove_general_weekday_notif(chat_id, direction, weekday, weekday_notif_dict)
    else:
        dir_notif_dict = ref.get()
        # Check if there is any notification set for this direction
        if dir_notif_dict==None:
            return False

        # Delete from user's dictionary
        ref.delete()
        # Delete from general users' notifications dictionary
        for weekday in dir_notif_dict:
            remove_general_weekday_notif(chat_id, direction, weekday, dir_notif_dict[weekday])

    return True

def delete_request_notification(chat_id, direction, weekday=None):
    """Deletes the requests' notifications for a given user, direction and week
    day.

    Parameters
    ----------
    chat_id : int or string
        chat_id of the user for whom to delete the notifications.
    direction : string
        Direction of the trip for notifications. Can be 'toBenalmadena' or 'toUMA'.
    weekday : string
        Optional. Week day for the notifications.
        Must be 'All days' or one from ('Monday', ..., 'Sunday').
        If not passed, the deletion will be done for the whole direction.

    Returns
    -------
    boolean
        True if the deletion was successfull, False if the notification for the
        chosen direction and weekday was not already configured.

    """
    def remove_general_weekday_notif(chat_id, direction, weekday):
        """Auxiliary function for other notification database functions"""
        # General users' notifications dictionary
        ref2 = db.reference(f"/Notifications/Requests/{direction}/{weekday}")
        # Delete from general users' notifications dictionary
        ref2.child(str(chat_id)).delete()

    # Driver's requests notifications dictionary
    ref = db.reference(f"/Drivers/{chat_id}/Request Notifications/{direction}")

    if weekday:
        if weekday not in weekdays_en+['All days']:
            raise ValueError("weekday doesn't have a valid value")
        weekday_notif_dict = ref.child(weekday).get()
        # Check if notification setting exists for this week day
        if weekday_notif_dict==None:
            return False

        # Delete from user's dictionary
        ref.child(weekday).delete()
        # Delete from general users' notifications dictionary
        remove_general_weekday_notif(chat_id, direction, weekday)
    else:
        dir_notif_dict = ref.get()
        # Check if there is any notification set for this direction
        if dir_notif_dict==None:
            return False

        # Delete from user's dictionary
        ref.delete()
        # Delete from general users' notifications dictionary
        for weekday in dir_notif_dict:
            remove_general_weekday_notif(chat_id, direction, weekday)

    return True
