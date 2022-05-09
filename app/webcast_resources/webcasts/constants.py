"""
Store some constants related to "webcasts"
"""

# maximum length constraints
COMMAN_MAX_LENGTH = 256
DESCRIPTION_MAX_LENGTH = 9216
PHONE_MAX_LENGTH = 32
EMAIL_MAX_LENGTH = 128


# for filters
MNFT_ALL = 'all'
MNFT_MINE = 'mine'
MNFT_INVITED = 'invited'
MNFT_PARTICIPATED = 'participated'
MNFT_HOSTED = 'hosted'
WEBCAST_LISTS = [MNFT_ALL, MNFT_MINE, MNFT_INVITED, MNFT_PARTICIPATED,
                 MNFT_HOSTED]
WEBCAST_LIST_CHOICES = [(v, v) for v in WEBCAST_LISTS]
