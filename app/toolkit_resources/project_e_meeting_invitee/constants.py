"""
Store some constants related to the Emeeting_invitee module
"""

# maximum length constraints
INVITEE_EMAIL_MAX_LENGTH = 128
INVITEE_NAME_MAX_LENGTH = 128
INVITEE_DESIGNATION_MAX_LENGTH = 128

INVITED = 'invited'  # invitee invited
REGISTERED = 'registered'  # invitee registered
WBNR_INV_STATUS_TYPES = [INVITED, REGISTERED]
WBNR_INV_STATUS_CHOICES = [(v, v) for v in WBNR_INV_STATUS_TYPES]
