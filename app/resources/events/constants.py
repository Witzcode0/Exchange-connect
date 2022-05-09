"""
Store some constants related to "events"
"""

# EVT_CONFERENCE_CALL = 'conference call'
# EVT_ANALYST_MEET = 'analyst meet'
# EVT_INVESTOR_DAY = 'investor day'
# EVT_INTERIM_RES = 'interim result annoucement'
# EVT_AGM = 'agm'
# EVT_EGM = 'egm'
# EVT_RESULTS = 'results'
# EVT_CONFERENCE = 'conference'
# EVENT_TYPES = [EVT_CONFERENCE_CALL, EVT_ANALYST_MEET, EVT_INVESTOR_DAY,
#                EVT_INTERIM_RES, EVT_AGM, EVT_EGM,
#                EVT_RESULTS, EVT_CONFERENCE]
# EVENT_TYPE_CHOICES = [(v, v) for v in EVENT_TYPES]

EVT_LANG_ENG = 'english'
EVT_LANG_CH_SMPL = 'chinese (simplified)'
EVT_LANG_CH_TRAD = 'chinese (traditional)'
EVENT_LANGUAGE_TYPES = [EVT_LANG_ENG, EVT_LANG_CH_SMPL, EVT_LANG_CH_TRAD]
EVENT_LANGUAGE_CHOICES = [(v, v) for v in EVENT_LANGUAGE_TYPES]

MNFT_ALL = 'all'
MNFT_MINE = 'mine'
MNFT_INVITED = 'invited'
MNFT_REQUESTED = 'requested'
EVENT_LISTS = [MNFT_ALL, MNFT_MINE, MNFT_INVITED, MNFT_REQUESTED]
EVENT_LIST_CHOICES = [(v, v) for v in EVENT_LISTS]

# length constraints
PLACE_MAX_LENGTH = 256
COMPANY_NAME_MAX_LENGTH = 256
SUBJECT_MAX_LENGTH = 512
DESCRIPTION_MAX_LENGTH = 9216
DIALINDETAILS_MAX_LENGTH = 1024
