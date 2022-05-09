"""
Store some constants related to the event collaborators module
"""

COL_PER_RSVP_EDIT = 'rsvp_edit'
COL_PER_RSVP_ADD = 'rsvp_add'
COL_PER_SLOT_EDIT = 'slot_edit'
COL_PER_SLOT_ADD = 'slot_add'
COL_PER_TYPES = [COL_PER_RSVP_EDIT, COL_PER_RSVP_ADD,
                 COL_PER_SLOT_EDIT, COL_PER_RSVP_EDIT]
# for direct use in model definition
COL_PER_TYPES_CHOICES = [(v, v) for v in COL_PER_TYPES]
