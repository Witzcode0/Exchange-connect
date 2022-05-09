"""
Store some constants related to "corporate access event inquiries"
"""

CANCEL = 'cancel'
RESCHEDULE = 'reschedule'
GENERAL = 'general'

E_MEETING_STATUS_TYPES = [CANCEL, RESCHEDULE, GENERAL]
E_MEETING_STATUS_CHOICES = [
    (v, v) for v in E_MEETING_STATUS_TYPES]
