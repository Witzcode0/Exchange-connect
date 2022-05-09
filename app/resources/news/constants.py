"""
Store some constants related to "news"
"""

NTAGS_ECONOMICS = 'economics'
NTAGS_BUSINESS = 'business'
NTAGS_MARKETS = 'markets'
# available agency pushes
NTAGS_BSE_INDIA = 'bse India'
NTAGS_REUTERS = 'reuters'
NTAGS_FINANCIAL_TIMES = 'financial times'
NTAGS_MONEY_CONTROL = 'money control'
NGTGS_GLOB_ECO = 'global economics'
NGTGS_BUSINESSWEEK = 'businessweek'
NGTGS_BUSINESSNEWS = 'businessnews'
NTAGS_TYPES = [NTAGS_BSE_INDIA, NTAGS_REUTERS,
               NTAGS_FINANCIAL_TIMES, NTAGS_MONEY_CONTROL,
               NTAGS_ECONOMICS, NTAGS_BUSINESS, NTAGS_MARKETS, NGTGS_GLOB_ECO,
               NGTGS_BUSINESSWEEK, NGTGS_BUSINESSNEWS]
# for direct use in model definition
NTAGS_TYPES_CHOICES = [(v, v) for v in NTAGS_TYPES]

# news tags
NEWS_FIN = 'financial'
NEWS_MARKET = 'markets'
NEWS_BUSINESS = 'business'
NEWS_ECON = 'economy'
NEWS_TAGS = [NEWS_FIN, NEWS_MARKET, NEWS_BUSINESS, NEWS_ECON]

SHORT_DESC_LENGTH = 250