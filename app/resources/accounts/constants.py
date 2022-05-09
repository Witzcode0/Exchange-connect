"""
Store some constants related to "accounts"
"""

ACCT_CORPORATE = 'corporate'
ACCT_BUY_SIDE_ANALYST = 'buy-side'
ACCT_SELL_SIDE_ANALYST = 'sell-side'
ACCT_GENERAL_INVESTOR = 'general investor'
ACCT_ADMIN = 'admin'
ACCT_GUEST = 'guest'
ACCT_PRIVATE = 'private'
ACCT_SME = 'sme'
ACCT_CORP_GROUP = 'corporate-group'
CRM_ACCT_TYPES = [ACCT_CORPORATE, ACCT_BUY_SIDE_ANALYST,
                  ACCT_SELL_SIDE_ANALYST, ACCT_GENERAL_INVESTOR, ACCT_PRIVATE,
                  ACCT_SME, ACCT_CORP_GROUP, ACCT_GUEST]
ACCT_TYPES = CRM_ACCT_TYPES[:]
ACCT_TYPES.extend([ACCT_ADMIN])
# for direct use in model definition
CRM_ACCT_TYPES_CHOICES = [(v, v) for v in CRM_ACCT_TYPES]
ACCT_TYPES_CHOICES = [(v, v) for v in ACCT_TYPES]

PROJECT_APX_ACCT_TYPES = [ACCT_CORPORATE, ACCT_PRIVATE, ACCT_CORP_GROUP]
PROJECT_APX_ACCT_TYPE_CHOICES = [(x,x) for x in PROJECT_APX_ACCT_TYPES]
# for default guest account name
DGA_NAME = 'default_guest_account'
# maximum length constraints
NAME_MAX_LENGTH = 512
# **Note: if these permissions change, review guest user convert to full
# fledged user flow
GU_ENDPOINT_PERMISSIONS = {
    'GET': ['corporate_access_api.corporateaccesseventapi',
            'corporate_access_api.corporateaccesseventlistapi',
            'corporate_access_api.corporateaccesseventslotlistapi',
            'corporate_access_api.corporateaccesseventinquiryapi',
            'corporate_access_api.corporateaccesseventinquirylistapi',
            'corporate_access_api.corporateaccesseventattendeelistapi',
            'corporate_access_api.corporateaccesseventstatsoverallapi',
            'corporate_access_api.carefeventtypelistapi',
            'corporate_access_api.carefeventsubtypelistapi',
            'webcast_api.webcastapi',
            'webcast_api.webcastattendeelistapi',
            'webcast_api.webcastlistapi',
            'webcast_api.webcaststatsoverallapi',
            'webinar_api.webinarstatsoverallapi',
            'webinar_api.webinarlistapi',
            'webinar_api.webinarapi',
            'api.userroleapi',
            'survey_api.surveyoverallstatsapi'],
    'PUT': ['corporate_access_api.corporateaccesseventslotapi',
            'corporate_access_api.corporateaccesseventinquiryapi',
            'corporate_access_api.corporateaccesseventattendeeapi',
            'corporate_access_api.corporateaccesseventinviteejoinedapi',
            'webcast_api.webcastattendeeapi'],
    'POST': ['corporate_access_api.corporateaccesseventinquirypostapi',
             'webinar_api.webinarinviteeregisterpostapi',
             'corporate_access_api.corporateaccesseventinviteeregisterapi',
             'webcast_api.webcastinviteeregisterpostapi'],
    'DELETE': ['corporate_access_api.corporateaccesseventinquiryapi',
               'corporate_access_api.corporateaccesseventinviteejoinedapi',
               'webinar_api.webinarinviteeregisterpostapi',
               'webinar_api.webinarinviteeapi']
}

SELL_SIDE_ENDPOINTS_NOT_PERMISSION = {
    'POST': ['api.surveypostapi'],
    'PUT': ['api.surveyapi'],
    'DELETE': ['api.surveyapi'],
    'GET': []
}

BUY_SIDE_ENDPOINTS_NOT_PERMISSION = {
    'POST': ['api.surveypostapi'],
    'PUT': ['api.surveyapi'],
    'DELETE': ['api.surveyapi'],
    'GET': []
}

GENERAL_INVESTOR_ENDPOINTS_NOT_PERMISSION = {
    'POST': ['webinar_api.webinarpostapi', 'webcast_api.webcastpostapi'],
    'PUT': ['webinar_api.webinarapi', 'webcast_api.webcastapi'],
    'DELETE': ['webinar_api.webinarapi', 'webcast_api.webcastapi'],
    'GET': []
}

# add premium list
CORPORATE_ENDPOINTS_PREMIUM_PERMISSION = {
    'POST': ['corporate_access_api.corporateaccesseventpostapi',
             'api.surveypostapi', 'newswire_api.newswirepostpostapi'],
    'PUT': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi'],
    'DELETE': ['corporate_access_api.corporateaccesseventapi',
               'api.surveyapi', 'newswire_api.newswirepostapi'],
    'GET': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi']
}

# #TODO: may be change permissions according to type
# add premium list
PRIVATE_ENDPOINTS_PREMIUM_PERMISSION = {
    'POST': ['corporate_access_api.corporateaccesseventpostapi',
             'api.surveypostapi', 'newswire_api.newswirepostpostapi'],
    'PUT': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi'],
    'DELETE': ['corporate_access_api.corporateaccesseventapi',
               'api.surveyapi', 'newswire_api.newswirepostapi'],
    'GET': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi']
}

SME_ENDPOINTS_PREMIUM_PERMISSION = {
    'POST': ['corporate_access_api.corporateaccesseventpostapi',
             'api.surveypostapi', 'newswire_api.newswirepostpostapi'],
    'PUT': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi'],
    'DELETE': ['corporate_access_api.corporateaccesseventapi',
               'api.surveyapi', 'newswire_api.newswirepostapi'],
    'GET': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi']
}

CORP_GROUP_ENDPOINTS_PERMIUM_PERMISSION = {
    'POST': ['corporate_access_api.corporateaccesseventpostapi',
             'api.surveypostapi', 'newswire_api.newswirepostpostapi'],
    'PUT': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi'],
    'DELETE': ['corporate_access_api.corporateaccesseventapi',
               'api.surveyapi', 'newswire_api.newswirepostapi'],
    'GET': ['corporate_access_api.corporateaccesseventapi',
            'api.surveyapi', 'newswire_api.newswirepostapi']
}

