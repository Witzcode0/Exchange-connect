"""
Store some constants related to "user"
"""

import pytz

ALL_TIMEZONES = pytz.all_timezones
# for direct use in model definition
ALL_TIMEZONES_CHOICES = [(v, v) for v in ALL_TIMEZONES]

DEF_TIMEZONE = 'Asia/Calcutta'

# languages
LANG_EN = 'en'
AVAILABLE_LANGUAGES = [LANG_EN]
ALL_LANGUAGES_CHOICES = [(v, v) for v in AVAILABLE_LANGUAGES]
DEF_LANGUAGE = LANG_EN

# minimum/auto password length
AUTO_PASSWORD_LENGTH = 7
# max unsuccessful logins allowed
MAX_UNSUCCESSFUL_LOGINS = 10

# stats
USR_FILES = 'files'
USR_VIDEOS = 'videos'
USR_COMPS = 'companies'
USR_CONTS = 'contacts'
