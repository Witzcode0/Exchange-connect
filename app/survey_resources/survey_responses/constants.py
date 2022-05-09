"""
Store some constants related to "survey responses"
"""

# survey response status types
UNANSWERED = 'unanswered'
PARTIAL = 'partial'
ANSWERED = 'answered'
SURVEYRESPONSE_STATUS_TYPES = [UNANSWERED, PARTIAL, ANSWERED]
SURVEYRESPONSE_STATUS_TYPE_CHOICES = [
    (v, v) for v in SURVEYRESPONSE_STATUS_TYPES]

# maximum length constraints
NAME_MAX_LENGTH = 512
INVITEE_EMAIL_MAX_LENGTH = 128
