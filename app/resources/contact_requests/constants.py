"""
Store some constants related to "contact requests"
"""

# request statuses
CRT_SENT = 'sent'
CRT_ACCEPTED = 'accepted'
CRT_REJECTED = 'rejected'
CREQ_STATUS_TYPES = [CRT_SENT, CRT_ACCEPTED, CRT_REJECTED]
# # for direct use in model definition
CREQ_STATUS_TYPE_CHOICES = [(v, v) for v in CREQ_STATUS_TYPES]

# sender receiver filter types
CR_SRT_SEND = 'sender'
CR_SRT_RECV = 'receiver'
CREQ_SEND_RECV_TYPES = [CR_SRT_SEND, CR_SRT_RECV]
