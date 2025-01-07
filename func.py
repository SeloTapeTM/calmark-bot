import time
import schedule
import requests
import json
import Vars
from datetime import datetime, date, timedelta
from gcsa.google_calendar import GoogleCalendar
from google.oauth2 import service_account
from loguru import logger

def send_msg(msg):
    token = Vars.token
    chat_id = Vars.chat_id
    url = f"https://api.telegram.org/bot{token}"
    params = {"chat_id": chat_id, "text": msg}
    r = requests.get(url + "/sendMessage", params=params)
    r = r.json()
    return r

def parse_response(response):
    try:
        response = response.json()
        response = json.loads(response['d'])
        return response
    except Exception as e:
        logger.error(f"Error parsing response: {e}")
        return None

def login():
    try:
        # Login to the website
        url = "https://calmark.co.il/Pages/Feed.aspx/UserLogin"
        payload = {
            "phone": Vars.phone,
            "password": Vars.password
        }
        headers = {
            'accept': 'application/json, text/javascript, */*; q=0.01',
            'content-type': 'application/json; charset=UTF-8',
            'key': 'undefined',
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Check if the response is successful
        if response.status_code != 200:
            logger.error(f"Login failed with status code {response.status_code}")
            return None

        parsed_response = parse_response(response)
        if parsed_response and 'response' in parsed_response:
            token = parsed_response['response']
            # with open('token.txt', 'w') as file:
            #     file.write(token)
            return token
        else:
            logger.error("Login failed: no response in the parsed data.")
            return None
    except requests.RequestException as e:
        logger.error(f"Request error during login: {e}")
        return None

def get_appointments(date=datetime.today().strftime('%d/%m/%Y %H:%M')):
    token = login()
    if not token:
        return []

    try:
        url = "https://calmark.co.il/Pages/Page.aspx/GetTimeAndDateForAppointmentByServiceAndEmployee"
        payload = {
            "businessId": 1884,
            "services": [8841],
            "employeeId": "2512",
            "date": date,
            "waitingList": False
        }
        headers = {
            'content-type': 'application/json; charset=UTF-8',
            'key': token
        }

        response = requests.post(url, headers=headers, data=json.dumps(payload))

        if response.status_code != 200:
            logger.error(f"Failed to fetch appointments with status code {response.status_code}")
            return []

        parsed_response = parse_response(response)
        if parsed_response:
            appointments = parsed_response[0].get('UnoccupiedTime', [])
            return appointments
        else:
            logger.error("Failed to parse appointments response.")
            return []
    except requests.RequestException as e:
        logger.error(f"Request error while fetching appointments: {e}")
        return []

def gc_init():
    credentials_path = Vars.sa_json
    credentials = service_account.Credentials.from_service_account_file(credentials_path,scopes=['https://www.googleapis.com/auth/calendar'])
    calendar = GoogleCalendar(Vars.email, credentials=credentials)
    return calendar

def get_haircut_event_id(events):
    for event in events:
        event_name = event.summary  # Get the event name
        logger.info(f'Checking event: {event_name}')
        if event_name == "JOB-Haircut":
            event_id =event.event_id
            logger.info(f'Found event named: {event_name} with id {event_id}')
            return event_id
        else:
            logger.info(f'Found event named: {event_name}, keep searching')
    return

def check_for_appointments():
    # Initialize Google Calendar
    logger.info(f'Checking for appointments in google calendar')
    try:
        # Calculate date range
        today = date.today()
        delta_min = timedelta(days=22)
        min_date = today + delta_min
        delta_max = timedelta(days=23)
        max_date = today + delta_max

        # init Google Calendar
        logger.info(f'init calendar')
        calendar = gc_init()
        
        # Fetch events from Google Calendar
        logger.info(f'fetch events')
        events = list(calendar.get_events(time_min=min_date, time_max=max_date))  # Convert to list
        event_id = get_haircut_event_id(events)

        # get specific event
        event = calendar.get_event(event_id=event_id)
        event_name = event.summary  # Get the event name
        logger.info(f'event name = {event_name}')
        if event_name == "JOB-Haircut":
            logger.info(f'check if event is already scheduled')
            if event.description != 'Scheduled' and event.description != 'Booked':
                logger.info(f'discovered appointment at: {event.start} which is not scheduled, scheduling...')
                # Input date string
                input_date_str = event.start
                # Format the date to the desired output format
                output_date_str = input_date_str.strftime('%Y-%m-%dT%H:%M')
                # Parse the input date string into a datetime object
                hour = input_date_str.strftime("%H:%M") 
                # Print the output
                logger.info(f'Appointment found at date {output_date_str}')
                logger.info(f'Schedule job every day at {hour} to book the appointment')
                schedule.every().day.at(hour).do(book_appointment, date=output_date_str, event_id=event_id)
                msg = f"Scheduled a job tomorrow at {hour} to book the appointment"
                response = send_msg(msg)
                logger.info(f'response {response}')
                event.description = 'Scheduled'
                event.default_reminders = False
                event = calendar.update_event(event=event)
                event.add_popup_reminder(minutes_before_start=30)
                event.add_popup_reminder(minutes_before_start=360)
                event.add_popup_reminder(minutes_before_start=1440)
                event.add_popup_reminder(minutes_before_start=10080)
                event = calendar.update_event(event=event)
                logger.info(f'Scheduled a the job, updated event description, and updated the event to have 4 push reminders')
            else:
                logger.info(f'Found appointment - but it is already scheduled at {event.start}')
        else:
            logger.info(f'No appointment for date {input_date_str} found.')
    except Exception as e:
        logger.error(f"Error while checking appointments: {e}")

# def check_for_appointments():
    # # Initialize Google Calendar
    # logger.info(f'Checking for appointments in google calendar')
    # try:
        # logger.info(f'init calendar')
        # calendar = gc_init()
        # 
        # # Calculate date range
        # today = date.today()
        # delta_min = timedelta(days=22)
        # min_date = today + delta_min
        # delta_max = timedelta(days=23)
        # max_date = today + delta_max
# 
        # # Fetch events from Google Calendar
        # logger.info(f'fetch events')
        # events = list(calendar.get_events(time_min=min_date, time_max=max_date))  # Convert to list
        # input_date_str = events[0].start
        # logger.info(f'check if events is empty')
        # if events:
            # event_id = events[0].event_id
            # event = calendar.get_event(event_id=event_id)
            # event_name = event.summary  # Get the event name
            # logger.info(f'event name = {event_name}')
            # if event_name == "JOB-Haircut":
                # logger.info(f'check if event is already scheduled')
                # if event.description != 'Scheduled' and event.description != 'Booked':
                    # logger.info(f'discovered appointment at: {event.start} which is not scheduled, scheduling...')
                    # # Input date string
                    # input_date_str = event.start
                    # # Format the date to the desired output format
                    # output_date_str = input_date_str.strftime('%Y-%m-%dT%H:%M')
                    # # Parse the input date string into a datetime object
                    # hour = input_date_str.strftime("%H:%M")
                    # # Print the output
                    # logger.info(f'Appointment found at date {output_date_str}')
                    # logger.info(f'Schedule job every day at {hour} to book the appointment')
                    # schedule.every().day.at(hour).do(book_appointment, date=output_date_str, event_id=event_id)
                    # msg = f"Scheduled a job tomorrow at {hour} to book the appointment"
                    # response = send_msg(msg)
                    # event.description = 'Scheduled'
                    # event.default_reminders = False
                    # event = calendar.update_event(event=event)
                    # event.add_popup_reminder(minutes_before_start=30)
                    # event.add_popup_reminder(minutes_before_start=360)
                    # event.add_popup_reminder(minutes_before_start=1440)
                    # event.add_popup_reminder(minutes_before_start=10080)
                    # event = calendar.update_event(event=event)
                    # logger.info(f'Scheduled a the job, updated event description, and updated the event to have 4 push reminders')
                # else:
                    # logger.info(f'Found appointment - but it is already scheduled at {event.start}')
            # else:
                # logger.info(f'Found event but the name is wrong - {event_name}')
        # else:
            # logger.info(f'No appointment for date {input_date_str} found.')
    # except Exception as e:
        # logger.error(f"Error while checking appointments: {e}")

def book_appointment(date, event_id):
    time.sleep(30)
    token = login()
    if not token:
        return schedule.CancelJob
    
    # Retry configuration
    retries = 0
    max_retries = 20
    retry_interval = 120  # 2 minutes in seconds

    while retries < max_retries:
        token = login()
        if not token:
            return schedule.CancelJob
        # Check if the desired appointment is in the available appointments
        desired_appointment = datetime.fromisoformat(date).strftime('%d/%m/%Y %H:%M')
        # If the desired appointment is found, attempt to book it
        try:
            url = "https://calmark.co.il/Pages/Page.aspx/ScheduleAppointment"
            payload = {
                "businessId": 1884,
                "services": [8841],
                "employeeId": "2512",
                "notes": "",
                "startDate": desired_appointment,
                "source": None,
                "referrer": "https://calmark.co.il/",
                "targetSource": None
            }
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-language': 'en-US,en;q=0.9,he-IL;q=0.8,he;q=0.7',
                'content-type': 'application/json; charset=UTF-8',
                'key': token,
                'Cookie': 'language=he'
            }

            response = requests.post(url, headers=headers, data=json.dumps(payload))

            if response.status_code == 200:
                parsed_response = parse_response(response)
                if parsed_response and 'Appointment' in parsed_response:
                    logger.info(f"Appointment successfully booked for {parsed_response['Appointment']['StartDate']}")
                    # Update the event to be appointed.
                    gc = gc_init()
                    event = gc.get_event(event_id=event_id)
                    event.description = 'Booked'
                    event = gc.update_event(event=event)
                    dt = parsed_response['Appointment']['StartDate']
                    logger.info(f"dt: {dt}")
                    logger.info(f"dt type: {type(dt)}")
                    msg = f"Appointment successfully booked for {dt}. Go check it out at https://calmark.io/page/1884"
                    response = send_msg(msg)
                    logger.info(f"response from send_msg: {response}")
                    return schedule.CancelJob
                else:
                    logger.error("Failed to parse the appointment booking response.")
            else:
                logger.error(f"Failed to book appointment with status code {response.status_code}")

        except requests.RequestException as e:
            logger.error(f"Request error during booking appointment: {e}")

        # If we reach this point, either an error occurred or the appointment was not booked
        logger.info(f"Desired appointment ({desired_appointment}) not available or an error occurred. Retrying in 5 minutes...")
        retries += 1
        time.sleep(retry_interval)

    # If max retries reached, log failure and exit the job
    logger.error(f"Failed to book the desired appointment ({date}) after {max_retries} retries.")
    return schedule.CancelJob




            # if response.status_code == 200:
                # logger.error('Failed to book appointment (status 500).')
                # return
            # elif response.status_code != 200:
                # logger.error(f"Failed to book appointment with status code {response.status_code}")
                # return
# 
            # parsed_response = parse_response(response)
            # if parsed_response and 'Appointment' in parsed_response:
                # logger.info(f"Appointment successfully booked for {parsed_response['Appointment']['StartDate']}")
                # return schedule.CancelJob
            # else:
                # logger.error("Failed to parse the appointment booking response.")
                # return schedule.CancelJob
        # except requests.RequestException as e:
            # logger.error(f"Request error during booking appointment: {e}")
            # return schedule.CancelJob
# 
        # # If the desired appointment is not available, retry after waiting
        # logger.info(f"Desired appointment ({desired_appointment}) not available. Retrying in 10 minutes...")
        # retries += 1
        # time.sleep(retry_interval)
# 
    # # If max retries reached, log failure and exit the job
    # logger.error(f"Failed to book the desired appointment ({date}) after {max_retries} retries.")
    # return schedule.CancelJob

# def book_appointment(date):
#     token = login()
#     if not token:
#         return schedule.CancelJob

#     try:
#         url = "https://calmark.co.il/Pages/Page.aspx/ScheduleAppointment"
#         # Format the date like this: "22/11/2024 11:00"
#         date = datetime.fromisoformat(date).strftime('%d/%m/%Y %H:%M')
#         payload = {
#             "businessId": 1884,
#             "services": [8841],
#             "employeeId": "2512",
#             "notes": "",
#             "startDate": date,
#             "source": None,
#             "referrer": "https://calmark.co.il/",
#             "targetSource": None
#         }
#         headers = {
#             'accept': 'application/json, text/javascript, */*; q=0.01',
#             'accept-language': 'en-US,en;q=0.9,he-IL;q=0.8,he;q=0.7',
#             'content-type': 'application/json; charset=UTF-8',
#             'key': token,
#             'Cookie': 'language=he'
#         }

#         response = requests.post(url, headers=headers, data=json.dumps(payload))

#         if response.status_code == 500:
#             logger.error('Failed to book appointment (status 500).')
#             return schedule.CancelJob
#         elif response.status_code != 200:
#             logger.error(f"Failed to book appointment with status code {response.status_code}")
#             return schedule.CancelJob

#         parsed_response = parse_response(response)
#         if parsed_response and 'Appointment' in parsed_response:
#             print(f'Appointment booked for {appoointment}')
#             return schedule.CancelJob
#         else:
#             logger.error("Failed to parse the appointment booking response.")
#     except requests.RequestException as e:
#         logger.error(f"Request error during booking appointment: {e}")
