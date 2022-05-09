"""
Store some constants related to "event invites"
"""

INVITED = 'invited'  # invite invited
REJECTED = 'rejected'  # invite/request rejected
ACCEPTED = 'accepted'  # invite/request accepted
REQUESTED = 'requested'  # request requested
MAYBE = 'maybe'  # invite maybe
NOT_ATTENDED = 'not_attended'
ATTENDED = 'attended'

EVT_INV_STATUS_TYPES = [INVITED, REJECTED, ACCEPTED, REQUESTED, MAYBE,
                        NOT_ATTENDED, ATTENDED]
EVT_INV_STATUS_CHOICES = [(v, v) for v in EVT_INV_STATUS_TYPES]

# length constraints
COMMENT_MAX_LENGTH = 1024
