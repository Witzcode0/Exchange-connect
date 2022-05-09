"""
Store some constants related to "reminders"
"""

# system reminder types
RST_DEFAULT = 'default'  # 30 minutes before
RST_USER = 'user'
REMINDER_SYS_TYPES = [RST_DEFAULT, RST_USER]
# for direct use in model definition
REMINDER_SYS_TYPES_CHOICES = [(v, v) for v in REMINDER_SYS_TYPES]
