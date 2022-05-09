"""
Store some constants related to "invitee status"
"""

# request statuses
PVSTATUS_PENDING = 'pending'
PVSTATUS_INTERESTED = 'interested'
PVSTATUS_NOT_INTERESTED = 'not interested'

PV_STATUS_TYPES = [PVSTATUS_PENDING, PVSTATUS_INTERESTED, PVSTATUS_NOT_INTERESTED]
# # for direct use in model definition
PV_STATUS_TYPE_CHOICES = [(v, v) for v in PV_STATUS_TYPES]