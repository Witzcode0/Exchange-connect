"""
Store some constants related to "Emeeting"
"""

# maximum length constraints
COMMON_MAX_LENGTH = 256
AGENDA_MAX_LENGTH = 9216
PHONE_MAX_LENGTH = 32
EMAIL_MAX_LENGTH = 128

MNFT_ALL = 'all'
MNFT_MINE = 'mine'
MNFT_INVITED = 'invited'
MEETING_LISTS = [MNFT_ALL, MNFT_MINE, MNFT_INVITED]
MEETING_LIST_CHOICES = [(v, v) for v in MEETING_LISTS]
