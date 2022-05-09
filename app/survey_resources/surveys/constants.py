"""
Store some constants related to "surveys"
"""

# survey status types
OPEN = 'open'
RUNNING = 'running'
CLOSED = 'closed'
SURVEY_STATUS_TYPES = [OPEN, RUNNING, CLOSED]
SURVEY_STATUS_TYPE_CHOICES = [(v, v) for v in SURVEY_STATUS_TYPES]

# maximum length constraints
TITLE_MAX_LENGTH = 512
