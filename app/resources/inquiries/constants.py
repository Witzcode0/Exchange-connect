"""
Store some constants related to "inquiries"
"""

# inquiry types
INQT_CONTACT = 'contact-us'
INQT_PLAN_QUOTE = 'plan-quote'
INQ_TYPE_TYPES = [INQT_CONTACT, INQT_PLAN_QUOTE]
# # for direct use in model definition
INQ_TYPE_TYPE_CHOICES = [(v, v) for v in INQ_TYPE_TYPES]

# plan quote sub types
INQT_PLQ_FREE = 'free'
INQT_PLQ_PREMIUM = 'premium'
INQT_PLQ_ENTERPRISE = 'enterprise'
INQT_PLQ_TYPES = [INQT_PLQ_FREE, INQT_PLQ_PREMIUM, INQT_PLQ_ENTERPRISE]
INQT_PLQ_TYPE_CHOICES = [(v, v) for v in INQT_PLQ_TYPES]
# #TODO: add more sub types according to inquiry type?
# # for direct use in model definition
INQT_ALL_TYPE_CHOICES = INQT_PLQ_TYPE_CHOICES[:]

# maximum length constraints
NAME_EMAIL_MAX_LENGTH = 128
MESSAGE_MAX_LENGTH = 4096
REMARKS_MAX_LENGTH = 1024
CONTACT_NUMBER_MAX_LENGTH = 32
SUBJECT_MAX_LENGTH = 512
