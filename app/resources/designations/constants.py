"""
Store some constants related to "designations"
"""

# maximum length constraints
NAME_MAX_LENGTH = 256

# designation level
DES_LEVEL_BOD = 'bod & top management'
DES_LEVEL_MID = 'mid-level management'
DES_LEVEL_OTH = 'managers & others'
DES_LEVEL_TYPES = [DES_LEVEL_BOD, DES_LEVEL_MID, DES_LEVEL_OTH]
DES_LEVEL_TYPES_CHOICES = [(v, v) for v in DES_LEVEL_TYPES]
