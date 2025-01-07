import Vars
import time
import schedule
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar
from gcsa.recurrence import Recurrence, DAILY, SU, SA
from func import book_appointment, check_for_appointments, send_msg
from loguru import logger

send_msg("test")

schedule.every().day.at("23:45").do(check_for_appointments)

logger.info(f'Start while loop to check for pending jobs')

while True:
    schedule.run_pending()
    time.sleep(1)

logger.info(f'If you see this, then something is broken with your code.. SMH')
send_msg("If you see this, then something is broken with your code.. SMH")
