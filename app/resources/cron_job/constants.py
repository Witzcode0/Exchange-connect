"""
Store some constants related to "crontab"
"""
SEND_NEWS_EMAIL_INDIA = 'send-news-email-india'
SEND_NEWS_EMAIL_UAE = 'send-new-email-uae'
SEND_FEEDITEMS = 'update-feeditems'
SEND_SCHEDULED_REPORT = 'send-scheduled-reports'
DEACTIVATE_SCHEDULED_REPORTS = 'deactivate-scheduled-reports'
RESET_REPORT_DOWNLOADED = 'reset-report-downloaded'
UPDATE_TWITTER_FEED = 'update_twitter_feed'
DELETE_INDEITEMS = 'delete_indexitems'
CRON_TYPES_LIST = [
	SEND_NEWS_EMAIL_INDIA,
	SEND_NEWS_EMAIL_UAE,
	SEND_FEEDITEMS,
	SEND_SCHEDULED_REPORT,
	DEACTIVATE_SCHEDULED_REPORTS,
	RESET_REPORT_DOWNLOADED,
	UPDATE_TWITTER_FEED,
	DELETE_INDEITEMS]

# for direct use in model definition
CRONJOB_TYPES = [(v,v) for v in CRON_TYPES_LIST]

EACH_MINUTES = 'minutes'
EACH_HOURS = 'hours'

CRON_EACH_LIST = [EACH_HOURS,EACH_MINUTES]

CRONJOB_EACH_TYPES = [(v,v) for v in CRON_EACH_LIST]
