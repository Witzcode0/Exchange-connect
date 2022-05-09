"""
Store some constants related to the entire app
"""

# DB error messages
DB_ALREADY_EXISTS = 'already exists'
DB_NOT_PRESENT = 'not present'

# error messages
# minlength 1, i.e non empty values
MSG_NON_EMPTY = 'Can not be empty'
# error messages
# maxlength, i.e not exceeds max value
MSG_LENGTH_EXCEEDS = 'Field Length Exceeds'
# DB Related error messsages
MSG_ALREADY_EXISTS = 'Already exists'
MSG_DOES_NOT_EXIST = 'Does not exist'
# error message if data not json formatted
MSG_NOT_JSON_FORMAT = 'Data not in JSON format'
# error message if data referenced another table
MSG_REF_OTHER_TABLE = 'It is still referenced from table'

VIDEO = tuple('mp4 mkv flv vob gif wmv amv 3gp mpg avi'.split())

FILETYP_VD = 'video'
FILETYP_AD = 'audio'
FILETYP_IM = 'image'
FILETYP_OT = 'other_file'

# file type for parsing company and account data
FILE_TYPES = ['vnd.ms-excel',
              'vnd.openxmlformats-officedocument.spreadsheetml.sheet']

# for thumbnail valid files
FOR_THUMBNAIL = tuple('doc docx xls xlsx jpg jpe jpeg png gif svg bmp'
                      ' txt pdf odt docm'.split())

# module names
MOD_EVENT = 'event'
MOD_POST = 'post'
MOD_ARCHIVE = 'archive_file'
MOD_USER_PROFILE = 'user_profile'
MOD_ACCOUNT_PROFILE = 'account_profile'
MOD_MGMT_PROFILE = 'management_profile'
MOD_CRM_CONTACT_PROFILE = 'crm_contact_file'
MOD_CRM_FILE_LIBRARY = 'crm_file_library'
MOD_NEWSWIRE_POST_FILE_LIBRARY = 'newswire_post_file_library'
MOD_COMPANY = 'company_page'
MOD_RESEARCH_REPORT = 'research_report'
MOD_IR_MODULE_PHOTO = 'ir_module_file'

#personalised video types
VID_TEASER = 'teaser'
VID_DEMO = 'demo'

VIDE_TYPES = [VID_TEASER, VID_DEMO]

# event type for verification
EVNT_CA_EVENT = 'ca_event'
EVNT_WEBINAR = 'webinar'
EVNT_PUBLIC_WEBINAR = 'public_webinar'
EVNT_WEBCAST = 'webcast'
EVNT_SURVEY = 'survey'
EVNT_DIST_LIST = 'distribution_list'
EVNT_EMEETING = 'e_meeting'
EVNT_NEWS_LETTER = 'news_letter'
EVNT_BSE_FEED = 'bse_announcement'

# Extra code for account subscription expired
EC_SUB_EXPIRED = 403001

# sequence id related message(used in CAEvent, Webinar amd Webcast)
SEQUENCE_ID_MIN_VALUE = 1
SEQUENCE_ID_MIN_VALUE_ERROR = 'sequence_id value must be greater than 0'

# strong password regex string
STRONG_PASSWORD = '^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])' \
                  '(?=.*[$@$!#%*?&])[A-Za-z\d$@$#!%*?&]{8,}$'

# for test mail type
DF_SUPPORT = 'support'
EVENT_SUPPORT = 'event_support'
TEST_MAIL_TYPES = [DF_SUPPORT, EVENT_SUPPORT]

# for unsubscribe from types
EVNT_UNSUB_FROM = [EVNT_CA_EVENT, EVNT_WEBINAR, EVNT_WEBCAST, EVNT_SURVEY,
                   EVNT_DIST_LIST,EVNT_NEWS_LETTER,EVNT_BSE_FEED]

EVNT_UNSUB_FROM_CHOICES = [(x, x) for x in EVNT_UNSUB_FROM]

EMAIL_SENT = 'Sent'
EMAIL_NOT_SENT = 'Not sent'
EMAIL_UNSUB = 'Unsubscribed'
EMAIL_STATUS = [EMAIL_SENT, EMAIL_NOT_SENT, EMAIL_UNSUB]
EMAIL_STATUS_CHOICES = [(x,x) for x in EMAIL_STATUS]
# default elastic search index name
DF_ES_INDEX = 'exchange-connect'
NW_ES_INDEX = 'daily-news'

# mail categories
DAILY_ANNOUNCEMENT = 'Daily Announcement'
DAILY_NEWSLETTER = 'Daily News Letter'
WEBCAST = 'Webcast'
WEBINAR = 'Webinar'
SCHEDULE_REPORTS = 'Schedule Report'
CORPORATE_EMAIL_TASK = 'Corporate Event'
EMEETING_EMAIL_TASK = 'E-meeting'
DISTRIBUTION_EMAIL_TASK = 'Distribution List'
HELPDESK_EMAIL = 'Help Desk'
INQUIRY_EMAIL = 'Inquiry'
SURVEY_EMAIL = 'Survey'
ERROR_EMAIL = 'Error Email'
TOOLKIT_EMAIL = 'Design Lab'
USER_ACTIVITY_EMAIL = 'User Activity'
NEW_DESCRIPTOR = 'New Descriptor'

EVENT_TYEPS = [
	DAILY_NEWSLETTER, WEBCAST, WEBINAR, SCHEDULE_REPORTS,
	CORPORATE_EMAIL_TASK, EMEETING_EMAIL_TASK, DISTRIBUTION_EMAIL_TASK,
	HELPDESK_EMAIL, INQUIRY_EMAIL, SURVEY_EMAIL, ERROR_EMAIL,
	TOOLKIT_EMAIL, USER_ACTIVITY_EMAIL
	]

EMAIL_TYEPS = [(v,v) for v in EVENT_TYEPS]
