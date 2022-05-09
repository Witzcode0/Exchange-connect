"""
Store some constants related to the project_file_archive module
"""

# maximum length constraints
REMARKS_MAX_LENGTH = 1024
VERSION_MAX_LENGTH = 32

# for filters
MNFT_ALL = 'all'
MNFT_MINE = 'mine'
MNFT_RECEIVED = 'received'
FILE_LISTS = [MNFT_ALL, MNFT_MINE, MNFT_RECEIVED]
FILE_LIST_CHOICES = [(v, v) for v in FILE_LISTS]
