"""
Store some constants related to "crm note"
"""

NOTE_PRIVATE = 'private'
NOTE_INDIVIDUAL = 'individual'
NOTE_TYPES = [NOTE_PRIVATE, NOTE_INDIVIDUAL]
# for direct use in model definition
NOTE_TYPES_CHOICES = [(v, v) for v in NOTE_TYPES]
