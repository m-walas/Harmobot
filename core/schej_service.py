import requests
from datetime import timedelta
from dateutil import parser, tz

def convert_to_local(time_str, time_offset_hours):
    """
    Convert an ISO formatted UTC time string to local time.

    Parameters:
        time_str (str): Time string in ISO format.
        time_offset_hours (int): Offset in hours to apply.

    Returns:
        datetime or None: Local datetime (without timezone info) or None if conversion fails.
    """
    try:
        dt_utc = parser.isoparse(time_str)
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=tz.UTC)
        local_dt = dt_utc + timedelta(hours=time_offset_hours)
        return local_dt.replace(tzinfo=None)
    except Exception:
        return None

def fetch_event_data(user_url):
    """
    Process a user-provided URL to retrieve event and response data.

    Event dates are used to compute the timeMin and timeMax parameters for fetching response data. 
    Response data is then obtained by appending '/responses' to the API event URL.

    Parameters:
        user_url (str): The URL provided by the user.

    Returns:
        dict: A dictionary with keys 'eventData' and 'responsesData'.
    """
    api_event_url = user_url.replace('/e/', '/api/events/')
    
    event_resp = requests.get(api_event_url)
    event_data = event_resp.json()
    
    dates = event_data.get('dates', [])
    if not dates:
        return {'eventData': event_data, 'responsesData': {}}
    
    dt_objects = [parser.isoparse(d) for d in dates]
    earliest = min(dt_objects)
    latest = max(dt_objects)
    time_min_str = earliest.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    time_max_str = (latest + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    responses_url = api_event_url + '/responses'
    
    resp_resp = requests.get(
        responses_url,
        params={'timeMin': time_min_str, 'timeMax': time_max_str}
    )
    responses_data = resp_resp.json()
    
    return {
        'eventData': event_data,
        'responsesData': responses_data
    }

def process_data(json_response, time_offset_hours=0):
    """
    Process JSON data from a Schej event.

    Parameters:
        json_response (dict): JSON data containing event and response information.
        time_offset_hours (int, optional): Offset in hours for local time conversion. Defaults to 0.

    Returns:
        tuple: A tuple containing:
            - participants (list): List of dictionaries with keys 'name', 'email',
                'availabilities' (list of (start, end) tuples), and 'ifNeeded'.
            - poll_dates (list): List of date strings in "YYYY-MM-DD" format.
            - day_ranges (dict): Dictionary mapping each date string to a tuple (local_start, local_end).
    """
    event_data = json_response.get('eventData', {})
    responses_data = json_response.get('responsesData', {})
    
    raw_dates = event_data.get('dates', [])
    poll_dates = []
    duration_h = event_data.get('duration', 8)
    day_ranges = {}
    
    for ds in raw_dates:
        try:
            dt_utc = parser.isoparse(ds)
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=tz.UTC)
            local_start = dt_utc + timedelta(hours=time_offset_hours)
            local_start = local_start.replace(tzinfo=None)
            local_end = local_start + timedelta(hours=duration_h)
            local_end = local_end.replace(tzinfo=None)
            date_str = local_start.date().isoformat()
            poll_dates.append(date_str)
            day_ranges[date_str] = (local_start, local_end)
        except Exception:
            pass
    
    user_info_map = {}
    event_responses = event_data.get('responses', {})
    
    for key_in_event, val in event_responses.items():
        name_top = val.get('name', '')
        user_obj = val.get('user')
        if user_obj:
            first_name = user_obj.get('firstName', '') or ''
            last_name = user_obj.get('lastName', '') or ''
            combined = (first_name + " " + last_name).strip()
            final_name = combined if not name_top.strip() and combined else name_top
        else:
            final_name = name_top
        
        possible_email = val.get('email', '')
        if user_obj and not possible_email.strip():
            possible_email = user_obj.get('email', '') or ''
        user_info_map[key_in_event] = {
            'name': final_name.strip(),
            'email': possible_email.strip()
        }
    
    participants = []
    for key_in_responses, resp_val in responses_data.items():
        info_dict = user_info_map.get(key_in_responses, {})
        name = info_dict.get('name', '')
        email = info_dict.get('email', '')
        if not name.strip():
            name = resp_val.get('name', '') or ''
        if not email.strip():
            email = resp_val.get('email', '') or ''
        if not name.strip():
            name = "Brak imienia"
        if not email.strip():
            email = "Brak emaila"
        avail = []
        for t in resp_val.get('availability', []):
            start_dt = convert_to_local(t, time_offset_hours)
            if start_dt:
                end_dt = start_dt + timedelta(minutes=15)
                avail.append((start_dt, end_dt))
        if_need = []
        for t in resp_val.get('ifNeeded', []):
            start_dt = convert_to_local(t, time_offset_hours)
            if start_dt:
                end_dt = start_dt + timedelta(minutes=15)
                if_need.append((start_dt, end_dt))
        participants.append({
            'name': name,
            'email': email,
            'availabilities': avail,
            'ifNeeded': if_need
        })
    
    return participants, poll_dates, day_ranges
