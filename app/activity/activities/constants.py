"""
Store some constants related to "activities"
"""

# activity type choice values
EAT_CC = 'conference call'
EAT_IM = 'investor meet'
EAT_QR = 'quaterly results'
EAT_AG = 'agm'
EAT_AM = 'analyst meet'
EAT_TK = 'task'
EAT_CA = 'call'
EAT_RS = 'roadshow'
EAT_MT = 'meeting'
ACTIVITY_TYPES = [EAT_CC, EAT_IM, EAT_QR, EAT_AG, EAT_AM, EAT_TK, EAT_CA,
                  EAT_RS, EAT_MT]
# for direct use in model definition
ACTIVITY_TYPES_CHOICES = [(v, v) for v in ACTIVITY_TYPES]

# activity subtype values
# for EAT_CA
EAST_CA_OUTBOUND = 'outbound'
EAST_CA_INBOUND = 'inbound'
ACTIVITY_SUB_TYPES = [EAST_CA_OUTBOUND, EAST_CA_INBOUND]

# status values
EST_ST = 'started'
EST_IP = 'in progress'
EST_CD = 'completed'
EST_DD = 'deferred'
ACTIVITY_STATUS_TYPES = [EST_ST, EST_IP, EST_CD, EST_DD]

# priority values
EPT_HTS = 'highest'
EPT_HT = 'high'
EPT_MM = 'medium'
EPT_LT = 'low'
EPT_LTS = 'lowest'
PRIORITY_TYPES = [EPT_HTS, EPT_HT, EPT_MM, EPT_LT, EPT_LTS]

# roadshow meeting types
MT_OO = 'one on one'
MT_GRP = 'group'
MEETING_TYPES = [MT_OO, MT_GRP]

# repeat values
ERT_WK = 'weekly'
ERT_DY = 'daily'
ERT_MN = 'monthly'
ERT_YR = 'yearly'
ERT_NN = '--'  # no repeat
REPEAT_TYPES = [ERT_WK, ERT_DY, ERT_MN, ERT_YR, ERT_NN]

# reminder frequency
RFT_WK = 'weekly'
RFT_DY = 'daily'
REMINDER_FREQUENCY_TYPES = [RFT_WK, RFT_DY]
# for direct use in model definition
REMINDER_FREQUENCY_TYPES_CHOICES = [(v, v) for v in REMINDER_FREQUENCY_TYPES]

# reminder types
RMT_NO = 'notification'
RMT_EM = 'email'
REMINDER_TYPES = [RMT_NO, RMT_EM]

# reminder units
RM_MINS= 'minutes'
RM_HOURS = 'hours'
RM_DAYS = 'days'
RM_WEEKS = 'weeks'
RM_UNITS = [RM_MINS, RM_HOURS, RM_DAYS, RM_WEEKS]
RM_UNITS_CHOICES = [(x, x) for x in RM_UNITS]

# account type
AC_BUYSIDE = 'Buy-side'
AC_SELLSIDE = 'Sell-side'
AC_TYPES = [AC_SELLSIDE, AC_BUYSIDE]
AC_TYPES_CHOICE = [(x,x) for x in AC_TYPES]
