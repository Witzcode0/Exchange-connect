"""
Store some constants related to "audio transcription status"
"""

AT_COMPLETED = 'completed'
AT_RUNNING = 'running'
AT_FAILED = 'failed'
AT_PENDING = 'pending'

AT_PROGRESS_TYPES = [AT_COMPLETED, AT_RUNNING, AT_FAILED, AT_PENDING]
# # for direct use in model definition
AT_PROGRESS_TYPE_CHOICES = [(v, v) for v in AT_PROGRESS_TYPES]