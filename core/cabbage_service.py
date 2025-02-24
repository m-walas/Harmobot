import requests
from datetime import timedelta, datetime
from dateutil import parser, tz
from urllib.parse import urlparse, urlunparse

def convert_to_local(time_str, time_offset_hours):
    """
    Convert an ISO-formatted UTC time string to local time by applying the specified offset.

    Args:
        time_str (str): An ISO-formatted time string.
        time_offset_hours (int or float): Hours to add for local time conversion.

    Returns:
        datetime or None: Local datetime (without timezone info) or None if conversion fails.
    """
    try:
        utc_time = parser.isoparse(time_str)
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=tz.UTC)
        local_time = utc_time + timedelta(hours=time_offset_hours)
        return local_time.replace(tzinfo=None)
    except Exception:
        return None

def fetch_event_data(user_url):
    """
    Convert a user-provided URL to the corresponding API URL and fetch event data.

    The conversion is performed by:
        1. Prepending "api." to the domain.
        2. Replacing the "/m/" segment in the URL's path with "/api/meetings/".

    Args:
        user_url (str): The URL provided by the user.

    Returns:
        dict: The JSON response from the API.

    Raises:
        Exception: If the HTTP request fails.
    """
    parsed = urlparse(user_url)
    if not parsed.netloc.startswith("api."):
        new_netloc = "api." + parsed.netloc
    else:
        new_netloc = parsed.netloc

    new_path = parsed.path.replace("/m/", "/api/meetings/", 1)
    api_url = urlunparse((parsed.scheme, new_netloc, new_path, parsed.params, parsed.query, parsed.fragment))
    
    headers = {"Accept": "application/json"}
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code: {response.status_code}")
    return response.json()

def process_data(json_response, time_offset_hours=0):
    """
    Process the JSON response and return participants, poll dates, and day ranges.

    The response is expected to include:
        - "tentativeDates": a list of date strings in "YYYY-MM-DD" format.
        - "respondents": a list of participant objects with "name" and "availabilities".
        - "minStartHour" and "maxEndHour" indicating daily time boundaries.

    Args:
        json_response (dict): JSON data from the event API.
        time_offset_hours (int or float, optional): Hours to adjust times to local time. Defaults to 0.

    Returns:
        tuple: A tuple containing:
            - participants (list): Each participant is a dict with keys 'name', 'email',
                'availabilities' (list of (start, end) tuples), and 'ifNeeded' (empty list).
            - poll_dates (list): List of date strings.
            - day_ranges (dict): Mapping of each date to a (local_start, local_end) tuple.
    """
    poll_dates = json_response.get("tentativeDates", [])
    respondents = json_response.get("respondents", [])
    participants = []

    for respondent in respondents:
        name = respondent.get("name", "Brak imienia")
        email = "Brak emaila"
        availabilities_raw = respondent.get("availabilities", [])
        avail_times = []
        for time_str in availabilities_raw:
            start_time = convert_to_local(time_str, time_offset_hours)
            if start_time:
                end_time = start_time + timedelta(minutes=30)
                avail_times.append((start_time, end_time))
        participants.append({
            'name': name,
            'email': email,
            'availabilities': avail_times,
            'ifNeeded': []  # note: cabbageMeet does not support the ifNeeded option -> empty list
        })

    min_start = json_response.get("minStartHour", 9)
    max_end = json_response.get("maxEndHour", 17)
    day_ranges = {}
    for date_str in poll_dates:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            local_start = dt.replace(hour=int(min_start), minute=0)
            local_end = dt.replace(hour=int(max_end), minute=0)
            day_ranges[date_str] = (local_start, local_end)
        except Exception:
            pass

    return participants, poll_dates, day_ranges
