from app.resources.menu import constants as MENU

ALL = 'All'
CAEVENT = 'CorporateAccessEvent'
WEBCAST = 'Webcast'
WEBINAR = 'Webinar'
ACCOUNT = 'AccountProfile'
CRM_DIST_LIST = 'CRMDistributionList'
CRM_CONTACT = 'CRMContact'
USER_PROFILE = 'UserProfile'
RESEARCH_REPORT = 'ResearchReport'
ANNOUNCEMENT = 'CorporateAnnouncement'

GLOBAL_SEARCH_FILTERS = [ALL, CAEVENT, WEBCAST, WEBINAR, ACCOUNT,
                         CRM_DIST_LIST, CRM_CONTACT, USER_PROFILE,
                         RESEARCH_REPORT, ANNOUNCEMENT]

MODULE_EXTRAS = {
    ACCOUNT: {'display_name': 'Company', 'priority': 1},
    CRM_CONTACT: {'display_name': 'Contact', 'priority': 2},
    USER_PROFILE: {'display_name': 'People', 'priority': 3},
    ANNOUNCEMENT: {'display_name': 'Announcement', 'priority': 4},
    CAEVENT: {'display_name': 'Event', 'priority': 5},
    WEBCAST: {'display_name': 'Webcast', 'priority': 6},
    WEBINAR: {'display_name': 'Webinar', 'priority': 7},
    CRM_DIST_LIST: {'display_name': 'Email Campaign', 'priority': 8},
    RESEARCH_REPORT: {'display_name': 'Research Report', 'priority': 9},
}

ALL_MODULES = [_ for _ in MODULE_EXTRAS]


# menu code and model name mapping
# this modules will only be searched if menu is permitted
MODULE_MENUCODE = {
    ACCOUNT: MENU.SEARCH_COMPANY,
    CRM_CONTACT: MENU.CRM,
    USER_PROFILE: MENU.CRM,
    CAEVENT: MENU.EVENTS,
    WEBCAST: MENU.WEBCAST,
    WEBINAR: MENU.WEBINAR,
    CRM_DIST_LIST: MENU.CRM,
    RESEARCH_REPORT: MENU.RESEARCH_REPORT
    }
