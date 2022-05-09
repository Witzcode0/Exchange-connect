"""
Store some constants related to "registration requests"
"""

# request statuses
REQ_ST_UNVERIFIED = 'unverified'  # email unverified
REQ_ST_PENDING = 'pending'  # email verified, no action taken yet
REQ_ST_ACCEPTED = 'accepted'  # request accepted
REQ_ST_REJECTED = 'rejected'  # request rejected
REQ_STATUS_TYPES = [REQ_ST_UNVERIFIED, REQ_ST_PENDING, REQ_ST_ACCEPTED,
                    REQ_ST_REJECTED, ]
# for direct use in model definition
REQ_STATUS_TYPES_CHOICES = [(v, v) for v in REQ_STATUS_TYPES]
# maximum length constraints
NAME_MAX_LENGTH = 128
