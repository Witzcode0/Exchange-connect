"""
Store some constants related to the corporate_access_event_invitees module
"""

# maximum length constraints
INVITEE_EMAIL_MAX_LENGTH = 128

INVITEE_NAME_MAX_LENGTH = 128
INVITEE_DESIGNATION_MAX_LENGTH = 128

INVITED = 'invited'  # invitee invited
JOINED = 'joined'  # invitee joined
REJECTED = 'rejected'  # invitee rejected
EVT_INV_STATUS_TYPES = [INVITED, JOINED, REJECTED]
EVT_INV_STATUS_CHOICES = [(v, v) for v in EVT_INV_STATUS_TYPES]
