"""
Store some constants related to "corporate access event slots"
"""

ONE_ON_ONE = 'one'
GROUP_MEETING = 'group'

CA_EVENT_SLOT_TYPES = [ONE_ON_ONE, GROUP_MEETING]
CA_EVENT_SLOT_CHOICES = [(v, v) for v in CA_EVENT_SLOT_TYPES]

# maximum length constraints
ADDRESS_MAX_LENGTH = 256
SLOT_NAME_MAX_LENGTH = 256
DESCRIPTION_NAME_MAX_LENGTH = 256
