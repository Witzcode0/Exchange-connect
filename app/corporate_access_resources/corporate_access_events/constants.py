"""
Store some constants related to "corporate access event"
"""

# maximum length constraints
COMMON_MAX_LENGTH = 256
DESCRIPTION_MAX_LENGTH = 9216
PHONE_MAX_LENGTH = 32
EMAIL_MAX_LENGTH = 128

# for filters
MNFT_ALL = 'all'
MNFT_MINE = 'mine'
MNFT_INVITED = 'invited'
MNFT_PARTICIPATED = 'participated'
MNFT_COLLABORATED = 'collaborated'
MNFT_HOSTED = 'hosted'
CA_EVENT_LISTS = [MNFT_ALL, MNFT_MINE, MNFT_INVITED, MNFT_PARTICIPATED,
                  MNFT_COLLABORATED, MNFT_HOSTED]
CA_EVENT_LIST_CHOICES = [(v, v) for v in CA_EVENT_LISTS]

NO_OF_INVITEE = 1
