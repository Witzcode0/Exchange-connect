"""
Store some constants related to "agency pushes"
"""

# available agency pushes
AGPS_BSE_INDIA = 'bse india'
AGPS_BLOOMBERG = 'bloomberg'
AGPS_REUTERS = 'reuters'
AGPS_FINANCIAL_TIMES = 'financial times'
AGPS_MONEY_CONTROL = 'money control'
AGPS_TYPES = [AGPS_BSE_INDIA, AGPS_BLOOMBERG, AGPS_REUTERS,
              AGPS_FINANCIAL_TIMES, AGPS_MONEY_CONTROL]
# for direct use in model definition
AGPS_TYPES_CHOICES = [(v, v) for v in AGPS_TYPES]
