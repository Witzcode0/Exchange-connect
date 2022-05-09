"""
Store some constants related to the webcast_invitee module
"""

# maximum length constraints
INVITEE_EMAIL_MAX_LENGTH = 128
INVITEE_NAME_MAX_LENGTH = 128
INVITEE_DSGN_MAX_LENGTH = 128

INVITED = 'invited'  # invitee invited
REGISTERED = 'registered'  # invitee registered
WBCT_INV_STATUS_TYPES = [INVITED, REGISTERED]
WBCT_INV_STATUS_CHOICES = [(v, v) for v in WBCT_INV_STATUS_TYPES]
