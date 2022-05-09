"""
Store some constants related to "corporate access event inquiries"
"""

INQUIRED = 'inquired'
CONFIRMED = 'confirmed'

CA_EVENT_INQUIRY_STATUS_TYPES = [INQUIRED, CONFIRMED]
CA_EVENT_INQUIRY_STATUS_CHOICES = [
    (v, v) for v in CA_EVENT_INQUIRY_STATUS_TYPES]

DELETED = 'deleted'
CA_HIS_EVENT_INQUIRY_STATUS_TYPES = CA_EVENT_INQUIRY_STATUS_TYPES + [DELETED]

CA_HIS_EVENT_INQUIRY_STATUS_CHOICES = [
    (v, v) for v in CA_HIS_EVENT_INQUIRY_STATUS_TYPES]

# for filters
MNFT_MINE = 'mine'
MNFT_EVENT_CREATED = 'event_created'
CA_INQUIRY_LISTS = [MNFT_MINE, MNFT_EVENT_CREATED]
CA_INQUIRY_LIST_CHOICES = [(v, v) for v in CA_INQUIRY_LISTS]