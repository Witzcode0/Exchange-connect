import os
import datetime

# Application Control Settings
DEBUG = not True  # flag for dev environment
PORT = 5000  # the port to use
S3_UPLOAD = True  # flag for s3 upload
SWAGGER_ENABLED = True  # flag for swagger docs visibility

# Define the application directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# some domain variables
FRONTEND_DOMAIN = 'https//csstaging.s-ancial.com'
FRONTEND_UAE_DOMAIN = 'https//www.exchangeconnect.ae'
EMAIL_VERIFY_PATH = 'registration_verify'
DIRECT_EMAIL_VERIFY_PATH = 'admin-registration-request'
PASSWORD_RESET_PATH = 'reset-password'
# event join paths are slightly more complicated
BASE_EVENT_JOIN_PATH = 'login?redirectTo='
CORPACCS_EVENT_JOIN_ADD_URL = '/application/corporate_access/' +\
    'event/event_detail?id='
#personalised-demo/teaser/token
PERSONALISED_VIDEO_JOIN_ADD_URL = '/personalized-demo/'
WEBINAR_EVENT_JOIN_ADD_URL = '/application/webinar/webinar_name?id='
WEBINAR_PUBLIC_EVENT_JOIN_ADD_URL = '/events?id='
WEBCAST_EVENT_JOIN_ADD_URL = '/application/webcasting/webcasting_name?id='
EMEETING_EVENT_JOIN_ADD_URL = '/application'
SURVEY_PARTICIPATE_ADD_URL = 'survey?id='
ORDER_PLACED_LOGIN_URL = 'application/ir_toolkit/my_projects/ir_project_detail?id='
CORPORATE_ANNOUNCEMENT_JOIN_ADD_URL = ''
UNSUBSCRIBE_PATH = 'unsubscribe-email?token='
DESIGN_LAB_IFRAME_URL = ""
# some variables for request urls for webinar
BIGMARKER_REQUEST_URL = 'https://www.bigmarker.com/api/v1/'
BIGMARKER_API_KEY = '220836de5049e71b2663'
BIGMARKER_CHANNEL_ID = 'exchangeconnect'

# bse announcement url
BSE_ANNOUNCEMENT_JOIN_ADD_URL = '/application/company/announcements?id='

SYSTEM_TIMEZONE = 'UTC'  # pytz timezone string
USER_DEFAULT_TIMEZONE = 'Asia/Calcutta'  # pytz timezone string

# default trial subscription period
DEF_TRIAL_PERIOD = datetime.timedelta(days=60)

# Define the database - we are working with
# Postgres database
# SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@192.168.0.22' +\
#     ':5432/exchange_connect_test'
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:postgres@localhost' +\
    ':5432/bse_corporate_solution'
SQLALCHEMY_EXTERNAL_DATABASE_URI = 'mssql+pymssql://sa:SrvDst@2020@13.127.129.70/Fsloader'
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
DATABASE_CONNECT_OPTIONS = {}

# shows list of possible endpoints, so disable it
ERROR_404_HELP = DEBUG
# swagger
SWAGGER = {
    'title': 'Corporate Solution',
    'uiversion': 2,
}
# brand name, also used in email subjects
BRAND_NAME = 'ExchangeConnect'
# these emails will be notified in case of any errors
DEVELOPER_EMAILS = ['vrushabh@s-ancial.com']
# default sender email address
DEFAULT_SENDER_EMAIL = 'support@exchangeconnect.in'
# default sender name
DEFAULT_SENDER_NAME = 'ExchangeConnect Support'
# default sign off name
DEFAULT_SIGN_OFF_NAME = 'Support Team ExchangeConnect'
# default corporate access sender email address
DEFAULT_CA_SENDER_EMAIL = 'events@exchangeconnect.in'
# default corporate access sender name
DEFAULT_CA_SENDER_NAME = 'ExchangeConnect Events'
# default registration request contact-person email
DEFAULT_REG_REQ_CONTACT_EMAILS = ['sunny.shah@arhamtechnosoft.co.in', 'vrushabh@s-ancial.com']
# default inquiry contact-person email
DEFAULT_INQUIRY_EMAILS = ['vrushabh@s-ancial.com']
# default admin, internal email
DEFAULT_ADMIN_EMAILS = ['sunny.shah@arhamtechnosoft.co.in', 'vrushabh@s-ancial.com']
NEWSLETTER_BCC_ADDRESS = ['vrushabh@s-ancial.com', 'kajal@s-ancial.com']
NEWSLETTER_UAE_BCC_ADDRESS = ['vrushabh@s-ancial.com']

# default descriptor admin email
DESCRIPTOR_CC_ADDRESS = ['vrushabh@s-ancial.com', 'kajal@s-ancial.com', 'sunny.shah@arhamtechnosoft.com']
DESCRIPTOR_TO_ADDRESS = ['kaushal@s-ancial.com']

# helpdesk number, which will be mentioned in the sent emails
#HELPDESK_NUMBER = '+919029361001'
HELPDESK_NUMBER = '+912223005006'
# helpdesk email, which will be mentioned in the sent emails
HELPDESK_EMAIL = 'support@s-ancial.com'
# this list of emails will always receive all helpdesk emails
HELPDESK_ADMIN_EMAILS = ['vrushabh@s-ancial.com',]
# CA helpdesk number, which will be mentioned in the sent emails
#CA_HELPDESK_NUMBER = '+919029361001'
CA_HELPDESK_NUMBER = '+912223005006'
# CA helpdesk email, which will be mentioned in the sent emails
CA_HELPDESK_EMAIL = 'events@s-ancial.com'
# default CAEvent support internal email
DEFAULT_CA_SUPPORT_EMAIL = 'vrushabh@s-ancial.com'
# default CAEvent support internal name
DEFAULT_CA_SUPPORT_NAME = 'supoprt'
DEFAULT_UPDATE_EMAIL = 'updates@exchangeconnect.in'
DEFAULT_UPDATE_NAME = 'Update'

# email-id for UAE
DEFAULT_UAE_UPDATE_NAME = 'ExchangeConnect Update'
DEFAULT_UAE_UPDATE_EMAIL = 'updates@exchangeconnect.ae'

# default static image urls in emails
# for corporate access events
DEFAULT_CA_EVENT_LOGO_URL = ''
# for webinars
DEFAULT_WN_EVENT_LOGO_URL = ''
# for webcasts
DEFAULT_WC_EVENT_LOGO_URL = ''

# Files, uploads related config
# max uploadable file size
# max size for the server video upload is 500mb
MAX_CONTENT_LENGTH = 250 * 1024 * 1024
# any extra allowed file types for upload
ALLOWED_FILES = tuple('pdf pptx ppt'.split())

# uploaded files
# user photos
USR_PROFILE_PHOTO_FOLDER = 'usrprofilephoto'
USR_COVER_PHOTO_FOLDER = 'usrcoverphoto'
# account photos
ACCT_PROFILE_PHOTO_FOLDER = 'acctprofilephoto'
ACCT_COVER_PHOTO_FOLDER = 'acctcoverphoto'
# corporate announcements
CORP_ANNC_TRANSCRIPT_FOLDER = 'corpannctranscript'
CORP_ANNC_AUDIO_FOLDER = 'corpanncaudio'
CORP_ANNC_VIDEO_FOLDER = 'corpanncvideo'
# file archives
ARCHIVE_FILE_FOLDER = 'archivefile'
# project file archives
PROJECT_ARCHIVE_FILE_FOLDER = 'projectarchivefile'
# personalised video file folder
PERSONALISED_VIDEO_FILE_FOLDER = 'personalisedvideofile'
# personalised video poster file
PERSONALISED_VIDEO_POSTER_FILE_FOLDER = 'personalisedvideoposterfile'
# personalised video demo file related
PERSONALISED_VIDEO_DEMO_FILE_FOLDER = 'personalisedvideodemofile'
# post library file
POST_FILE_FOLDER = 'postfile'
# event library file
EVENT_FILE_FOLDER = 'eventfile'
# company page library file
COMPANY_PAGE_FILE_FOLDER = 'companypagefile'
# management profile photo
MGMT_PROFILE_PHOTO_FOLDER = 'manageprofilephoto'
# webcast invite logo folder
WEBCAST_INVITE_LOGO_FILE_FOLDER = 'webcastinvitelogofile'
# webcast invite banner folder
WEBCAST_INVITE_BANNER_FILE_FOLDER = 'webcastinvitebannerfile'
# webcast video folder
WEBCAST_VIDEO_FILE_FOLDER = 'webcastvideofile'
# webcast audio folder
WEBCAST_AUDIO_FILE_FOLDER = 'webcastaudiofile'
# webinar invite logo folder
WEBINAR_INVITE_LOGO_FILE_FOLDER = 'webinarinvitelogofile'
# webinar invite banner folder
WEBINAR_INVITE_BANNER_FILE_FOLDER = 'webinarinvitebannerfile'
# webinar video folder
WEBINAR_VIDEO_FILE_FOLDER = 'webinarvideofile'
# webinar audio folder
WEBINAR_AUDIO_FILE_FOLDER = 'webinaraudiofile'
# corporate access event invite logo folder
CA_EVENT_INVITE_LOGO_FILE_FOLDER = 'caeventinvitelogofile'
# corporate access event invite banner folder
CA_EVENT_INVITE_BANNER_FILE_FOLDER = 'caeventinvitebannerfile'
# corporate access event video folder
CA_EVENT_VIDEO_FILE_FOLDER = 'caeventvideofile'
# corporate access event audio folder
CA_EVENT_AUDIO_FILE_FOLDER = 'caeventaudiofile'
# corporate access event transcript folder
CA_EVENT_TRANSCRIPT_FILE_FOLDER = 'caeventtranscriptfile'
# corporate access event attachment folder
CA_EVENT_ATTACHMENT_FILE_FOLDER = 'caeventattachmentfile'
# corporate access open meeting attachment folder
CA_OPEN_MEETING_ATTACHMENT_FILE_FOLDER = 'caopenmeetingattachmentfile'
# help ticket attachment folder name only (no directory separators)
HTICKET_ATTACH_FOLDER = 'hticketattachment'
# help ticket comment attachment folder name only (no directory separators)
HCOMMENT_ATTACH_FOLDER = 'hcommentattachment'
# news wire post logo file
NEWSWIRE_POST_LOGO_FOLDER = 'newswirepostlogofile'
# newswire post file attachment folder name
NEWSWIRE_POST_FILE_FOLDER = 'newswirepostfile'
# corporate announcement file attachment folder
CORPORATE_ANNOUNCEMENT_FILE_FOLDER = 'corporateannouncementfile'
CORPORATE_ANNOUNCEMENT_XML_FILE_FOLDER = 'corporateannouncementxmlfile'
# research report file attachment folder
RESEARCH_REPORT_FILE_FOLDER = 'researchreportfile'
RESEARCH_REPORT_XML_FILE_FOLDER = 'researchreportxmlfile'
# CRM contact profile photo folder
CRM_CONTACT_PROFILE_PHOTO_FOLDER = 'crmcontactprofilephoto'
# CRM Library file folder
CRM_LIBRARY_FILE_FOLDER = 'crmlibraryfile'
# CRM group icon folder
CRM_GROUP_ICON_FOLDER = 'crmgroupicon'
# CRM group contact import file folder
CRM_GROUP_CONTACT_IMPORT_FILE_FOLDER = 'crmgroupcontactimportfile'
# crm distribution attachment file folder
CRM_DISTLIST_ATTACH_FOLDER = 'crmdistlistattach'
# crm distribution file library folder
CRM_DIST_LIBRARY_FILE_FOLDER = 'crmdistlibraryfile'
# market performance file attachment folder
ACCOUNT_MARKET_PERFORMANCE_FILE_FOLDER = 'accountmarketperformancefile'
# Distributed file attachement folder
DISTRIBUTION_LIST_FILE_FOLDER = 'distributionlistfile'
ACTIVITY_DOCS_FOLDER = 'activitydocs'
# IR module photoghraph folder
IR_MODULE_PHOTO_FOLDER = 'irmodulephotographfile'
# Audio transcribe file folder
AUDIO_TRANSCRIBE_FILE_FOLDER = 'audiotranscribefile'
# research report parsing file folder
PARSING_FILE_FOLDER = 'parsingfile'
# thumbnail common folder
BASE_THUMBNAIL_FOLDER = 'thumbnail'
# base folder for uploads (**absolute path)
BASE_UPLOADS_FOLDER = '/tmp'
BASE_DOWNLOADS_FOLDER = '/tmp'
BASE_ICS_FILE_FOLDER = os.path.join(
    BASE_UPLOADS_FOLDER, 'ics_files')
# upload destination for user profile photo
UPLOADED_USRPROFILEPHOTO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, USR_PROFILE_PHOTO_FOLDER)
# upload destination for user cover photo
UPLOADED_USRCOVERPHOTO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, USR_COVER_PHOTO_FOLDER)
# upload destination for account profile photo
UPLOADED_ACCTPROFILEPHOTO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, ACCT_PROFILE_PHOTO_FOLDER)
# upload destination for account cover photo
UPLOADED_ACCTCOVERPHOTO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, ACCT_COVER_PHOTO_FOLDER)
# upload destination for corporate announcements transcript files
UPLOADED_CORPANNCTRANSCRIPT_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CORP_ANNC_TRANSCRIPT_FOLDER)
# upload destination for corporate announcements audio
UPLOADED_CORPANNCAUDIO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CORP_ANNC_AUDIO_FOLDER)
# upload destination for corporate announcements video
UPLOADED_CORPANNCVIDEO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CORP_ANNC_VIDEO_FOLDER)
# upload destination for file archives files
UPLOADED_ARCHIVEFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, ARCHIVE_FILE_FOLDER)
# upload destination for project file archives files
UPLOADED_PROJECTARCHIVEFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, PROJECT_ARCHIVE_FILE_FOLDER)
# upload destination for post files
UPLOADED_POSTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, POST_FILE_FOLDER)
# upload destination for event file
UPLOADED_EVENTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, EVENT_FILE_FOLDER)
# upload destination for company page file
UPLOADED_COMPANYPAGEFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, COMPANY_PAGE_FILE_FOLDER)
# upload destination for management profile photo
UPLOADED_MANAGEPROFILEPHOTO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, MGMT_PROFILE_PHOTO_FOLDER)
# upload destination for web cast invite logo file
UPLOADED_WEBCASTINVITELOGOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBCAST_INVITE_LOGO_FILE_FOLDER)
# upload destination for web cast invite banner file
UPLOADED_WEBCASTINVITEBANNERFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBCAST_INVITE_BANNER_FILE_FOLDER)
# upload destination for web cast video file
UPLOADED_WEBCASTVIDEOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBCAST_VIDEO_FILE_FOLDER)
# upload destination for web cast audio file
UPLOADED_WEBCASTAUDIOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBCAST_AUDIO_FILE_FOLDER)
# upload destination for web inar invite logo file
UPLOADED_WEBINARINVITELOGOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBINAR_INVITE_LOGO_FILE_FOLDER)
# upload destination for web inar invite banner file
UPLOADED_WEBINARINVITEBANNERFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBINAR_INVITE_BANNER_FILE_FOLDER)
# upload destination for web inar video file
UPLOADED_WEBINARVIDEOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBINAR_VIDEO_FILE_FOLDER)
# upload destination for web inar audio file
UPLOADED_WEBINARAUDIOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, WEBINAR_AUDIO_FILE_FOLDER)
# upload destination for corporate access event invite logo file
UPLOADED_CAEVENTINVITELOGOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_EVENT_INVITE_LOGO_FILE_FOLDER)
# upload destination for corporate access event invite banner file
UPLOADED_CAEVENTINVITEBANNERFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_EVENT_INVITE_BANNER_FILE_FOLDER)
# upload destination for corporate access event video file
UPLOADED_CAEVENTVIDEOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_EVENT_VIDEO_FILE_FOLDER)
# upload destination for corporate access event audio file
UPLOADED_CAEVENTAUDIOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_EVENT_AUDIO_FILE_FOLDER)
# upload destination for corporate access event audio file
UPLOADED_CAEVENTTRANSCRIPTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_EVENT_TRANSCRIPT_FILE_FOLDER)
# upload destination for corporate access event attachment file
UPLOADED_CAEVENTATTACHMENTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_EVENT_ATTACHMENT_FILE_FOLDER)
# upload destination for corporate access open meeting attachment file
UPLOADED_CAOPENMEETINGATTACHMENTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CA_OPEN_MEETING_ATTACHMENT_FILE_FOLDER)
# upload destination for 'hticketattachment'
UPLOADED_HTICKETATTACHMENT_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, HTICKET_ATTACH_FOLDER)
# upload destination for 'hcommentattachment'
UPLOADED_HCOMMENTATTACHMENT_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, HCOMMENT_ATTACH_FOLDER)
# upload destination for news wire post logo files
UPLOADED_NEWSWIREPOSTLOGOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, NEWSWIRE_POST_LOGO_FOLDER)
# upload destination for 'newswirepostfileattachment'
UPLOADED_NEWSWIREPOSTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, NEWSWIRE_POST_FILE_FOLDER)
# upload destination for 'corporateannouncementfile'
UPLOADED_CORPORATEANNOUNCEMENTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CORPORATE_ANNOUNCEMENT_FILE_FOLDER)
UPLOADED_CORPORATEANNOUNCEMENTXMLFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CORPORATE_ANNOUNCEMENT_XML_FILE_FOLDER)
# upload destination for 'researchreportfile'
UPLOADED_RESEARCHREPORTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, RESEARCH_REPORT_FILE_FOLDER)
UPLOADED_RESEARCHREPORTXMLFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, RESEARCH_REPORT_XML_FILE_FOLDER)
# upload destination for crm contact profile photo
UPLOADED_CRMCONTACTPROFILEPHOTO_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CRM_CONTACT_PROFILE_PHOTO_FOLDER)
# upload destination for crm library file
UPLOADED_CRMLIBRARYFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CRM_LIBRARY_FILE_FOLDER)
# uploaded destination for crm group icon
UPLOADED_CRMGROUPICON_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CRM_GROUP_ICON_FOLDER)
# uploaded destination for crm group contact import file
UPLOADED_CRMGROUPCONTACTIMPORTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CRM_GROUP_CONTACT_IMPORT_FILE_FOLDER)
UPLOADED_CRMDISTLISTATTACH_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CRM_DISTLIST_ATTACH_FOLDER)
# upload destination for crm library file
UPLOADED_CRMDISTLIBRARYFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, CRM_DIST_LIBRARY_FILE_FOLDER)
# upload destnation for 'accountmarketperformancefile'
UPLOADED_ACCOUNTMARKETPERFORMANCEFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, ACCOUNT_MARKET_PERFORMANCE_FILE_FOLDER)
# upload desination for 'distributionlistfile'
UPLOADED_DISTRIBUTIONLISTFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, DISTRIBUTION_LIST_FILE_FOLDER)

UPLOADED_ACTIVITYDOCUMENTS_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, ACTIVITY_DOCS_FOLDER)
# upload desination for 'distributionlistfile'
UPLOADED_IRMODULEPHOTOS_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, IR_MODULE_PHOTO_FOLDER)

# upload destination for 'audiotranscribefile'
UPLOADED_AUDIOTRANSCRIBEFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, AUDIO_TRANSCRIBE_FILE_FOLDER)

UPLOADED_PERSONALISEDVIDEOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, PERSONALISED_VIDEO_FILE_FOLDER)

# upload destination for 'personalisedvideoposterfile'
UPLOADED_PERSONALISEDVIDEOPOSTERFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, PERSONALISED_VIDEO_POSTER_FILE_FOLDER)
# upload destination for 'personalisedvideodemofile'
UPLOADED_PERSONALISEDVIDEODEMOFILE_DEST = os.path.join(
    BASE_UPLOADS_FOLDER, PERSONALISED_VIDEO_DEMO_FILE_FOLDER)


# S3, and AWS configs
S3_URL = 'https://s3.amazonaws.com'
S3_BUCKET = 'csstagingtest'
S3_SEMIDOCUMENT_BUCKET = 'csstagingsemidocumentation'
S3_THUMBNAIL_BUCKET = 'csstaging-thumbnails'
S3_MEDIUM_BUCKET = 'csstaging-medium'
S3_ACCESS_KEY = 'AKIAIWJNOTH3O5BASVAA'
S3_ACCESS_SECRET = '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'
AWS_REGION = 'ap-southeast-1'

# SES configs
AWS_SES_REGION = 'us-east-1'

# AWS SES Configset
CONFIGURATION_SET_ENABLE = True
CONFIGURATION_SET = "csdailymail_test"

# old
# SMTP_USERNAME = 'AKIAJ2LTCCHYCE7DKFNA'
# SMTP_PASSWORD = 'Atn2I/Uqo8PespS/ivE2I0trOaqX5m3mLw4wsXJEO94M'
# new
SMTP_USERNAME = 'AKIAXOTWCJPKHNOTKRVY'
SMTP_PASSWORD = 'BEWs6oAZDijI+jN61AB9gmHw98HEIjq4S9hJ85+Kbsd8'
SMTP_HOST = 'email-smtp.us-east-1.amazonaws.com'
SES_CUSTOM_TEMPLATE = 'custom-staging'
SES_CUSTOM_TEMPLATE_SUCCESS_URL = 'https://csstaging.s-ancial.com/application/account_settings'
SES_CUSTOM_TEMPLATE_FAILURE_URL = 'https://csstaging.s-ancial.com/application/account_settings'

# firebase configs
FIREBASE_URL = 'https://fcm.googleapis.com/fcm/send'
FIREBASE_KEY = 'Key=AAAAp13CM2o:APA91bG2KqXLaUrrp4ms1Rk4kHIdyMfGO-q32XoQSvZsITH3kVK-ClUJvVijd4gqYGMgJWVIJjTX0wxmvYAo9qCPuFzJiIloHq9ZyI1vGZd4y0d2oEzHq2uf-fwJZHXN3bV_1SGLs5x-'

# jwt related
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(minutes=240)
JWT_ACCESS_TOKEN_EXPIRES_MOBILE = datetime.timedelta(days=90)

# celery configuration
CELERY_BROKER_URL = 'amqp://admin:password@localhost:5672'
CELERY_ENABLE_UTC = True  # is true by default
CELERY_IMPORTS = ['queueapp.tasks', 'queueapp.feed_tasks',
                  'queueapp.notification_tasks', 'queueapp.user_stats_tasks',
                  'queueapp.thumbnail_tasks', 'queueapp.event_tasks',
                  'queueapp.helpdesk_tasks', 'queueapp.user_email_tasks',
                  'queueapp.inquiry_tasks',
                  'queueapp.surveys.email_tasks',
                  'queueapp.webcasts.stats_tasks',
                  'queueapp.webcasts.email_tasks',
                  'queueapp.webcasts.notification_tasks',
                  'queueapp.webinars.stats_tasks',
                  'queueapp.webinars.email_tasks',
                  'queueapp.webinars.notification_tasks',
                  'queueapp.webinars.request_tasks',
                  'queueapp.corporate_accesses.stats_tasks',
                  'queueapp.corporate_accesses.email_tasks',
                  'queueapp.corporate_accesses.notification_tasks',
                  'queueapp.toolkits.email_tasks', 'queueapp.semi_documentation.file_parsing_tasks',
                  'queueapp.bse_announcements.notification_tasks',
                  # 'queueapp.bse_announcements.email_tasks'
                  ]

# default reminder (un-editable) before interval
DEF_REMINDER_BEFORE = datetime.timedelta(minutes=30)

# default users who should be contacts for every user
DEFAULT_CONTACT_LIST = [2893,]

# Application threads. A common general assumption is
# using 2 per available processor cores - to handle
# incoming requests using one and performing background
# operations using the other.
THREADS_PER_PAGE = 2

# Enable protection agains *Cross-site Request Forgery (CSRF)*
CSRF_ENABLED = True

# Use a secure, unique and absolutely secret key for
# signing the data.
# CSRF_SESSION_KEY = open('', 'r').read()
#CSRF_SESSION_KEY = open('/home/webroot/.ssh.pub', 'r').read()
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# Secret key for signing cookies
SECRET_KEY = "secret"
JWT_ALGORITHM = 'HS256'
# JWT_PRIVATE_KEY = open('', 'r').read()
# JWT_PUBLIC_KEY = open('', 'r').read()


# logging
FILE_LOGGING = False
LOG_LEVEL = 'info'
LOG_FILE = '/path/to/logfile'
LOG_MAXBYTES = 10 * 1024 * 1024
LOG_BACKUPCOUNT = 10

SQLALCHEMY_LOG_LEVEL = 'info'
SQLALCHEMY_LOG_FILE = '/path/to/logfile'

# socket related config
SOCKET_QUEUE_URL = 'amqp://admin:password@localhost:5672/'

# thumbnail pixel
THUMBNAIL_PAGE = 0
THUMBNAIL_PIXEL = [160, 160]

# for check api call origin(Security purpose)
REQUEST_ORIGINS = ['http://csstaging.s-ancial.com', 'http://csadmin.s-ancial.com', 'https://csstaging.s-ancial.com',
                  'http://localhost:4203', 'http://localhost:4204', 'http://csadmin.s-ancial.com',
                  'https://reportservice.exchangeconnect.in:1234', 'http://192.168.0.118:4203', 'http://192.168.0.118:4204',
                  'http://192.168.0.127:4203', 'http://192.168.0.127:4204', 'http://exchangeconnect.hk', 'https://exchangeconnect.hk',
                  'http://www.exchangeconnect.hk', 'https://www.exchangeconnect.hk']
REQUEST_MOBILE_PLATFORMS = ['android', 'iphone', 'ipad']

# exclude account ids for news parsing without ltd
NEWS_EXCLUDE_COMP_IDS = [3900]
# elastic search host url
ELASTICSEARCH_URL = 'http://localhost:9200'
USE_ELASTIC_SEARCH = True

# scheduled report related keys
SEND_REPORT_DOMAIN = 'https://reportservice.exchangeconnect.in:1234/'  # domain of node service
REPORT_USER_EMAIL = 'scheduledreport@exchangeconnect.in'

# Twitter Api config
TWITTER_API_KEY = 'EwFjjou7WEo2hv8TtUGkxsQoA'
TWITTER_API_SECRET_KEY = 'lSdtewmCoHdsBbP6YbXt451hSGDaOcR3bLJYzKa8uuvzwWBTvv'
TWITTER_ACCESS_TOKEN = '744763604-QK698xYwCAfXFGGZZEbAzUg6UTu7VlO0FYnrrLN8'
TWITTER_ACCESS_TOKEN_SECRET = 'SqhnoRzadv2D9aiFBJP6QLEwnbrYxK802NolU3ZCPavLj'

# exclude account ids for twitter parsing without ltd
TWITTER_EXCLUDE_AC_IDS = []
DESIGNLAB_CONFIG = {'FRONTEND_DOMAIN': 'http://designlab.s-ancial.com'}

#bse feed related config
BSE_UNAME = "Ancial"
BSE_PASSWORD = "Ancial@345"
BSE_FEED_URL = "https://dfws.bseindia.com/DataFeedService/api/DataFeed/Get_CorpAnnouncement/w"
