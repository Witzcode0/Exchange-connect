
from app import db
from app.resources.accounts.models import Account
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.user_profiles.models import UserProfile
from app.resources.user_settings.models import UserSettings
from app.crm_resources.crm_contacts.models import CRMContact
from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList

from app.base import constants as APP
from app.global_search.helpers import add_to_index, remove_from_index

"""
Subscribe to sqlalchemy mapper events for sync data in elastic search
"""

index = APP.DF_ES_INDEX

search_tables = [
    #Account,
    #CorporateAnnouncement,
    #UserProfile,
    #UserSettings,
    #CRMContact,
    #Webinar,
    #Webcast,
    #CRMDistributionList'''
]

def after_insert(mapper, connection, target):
    add_to_index(index, target)


def after_update(mapper, connection, target):
    # checking for soft delete
    if hasattr(target, 'deleted') and target.deleted:
        remove_from_index(index, target)
    else:
        add_to_index(index, target, is_update=True)


def after_delete(mapper, connection, target):
    remove_from_index(index, target)


for table in search_tables:
    db.event.listen(table, 'after_insert', after_insert)
    db.event.listen(table, 'after_update', after_update)
    db.event.listen(table, 'after_delete', after_delete)
