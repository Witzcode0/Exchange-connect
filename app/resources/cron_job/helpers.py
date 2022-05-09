""" methods for cron_job"""
from datetime import datetime
import time

def convert_time_into_utc(time_obj,timezone):

	diff_seconds = datetime.strptime(
		time_obj.strftime("%H:%M:%S"), "%H:%M:%S") - datetime.strptime(timezone,"%H:%M")
	time_utc = time.strftime('%H:%M:%S', time.gmtime(diff_seconds.seconds))
	time_utc_obj = datetime.strptime(time_utc,"%H:%M:%S")
	return time_utc_obj
