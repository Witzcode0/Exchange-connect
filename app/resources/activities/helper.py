from flask import url_for

from app.resources.activities import constants as ACTIVITY


def insert_url(objs):
    """
    Loads the urls of link
    """
    for obj in objs:
        if ACTIVITY.USERPROFILE == obj['activity_type']:
            obj['link'] = url_for('api.userprofileapi', user_id=obj['row_id'])

        if ACTIVITY.WEBINAR == obj['activity_type']:
            obj['link'] = url_for(
                'webinar_api.webinarapi', row_id=obj['row_id'])

        if ACTIVITY.WEBCAST == obj['activity_type']:
            obj['link'] = url_for(
                'webcast_api.webcastapi', row_id=obj['row_id'])

        if ACTIVITY.ACCOUNTPROFILE == obj['activity_type']:
            obj['link'] = url_for(
                'api.accountprofileapi', account_id=obj['row_id'])

        if ACTIVITY.CORPORATE == obj['activity_type']:
            obj['link'] = url_for(
                'corporate_access_api.corporateaccesseventapi',
                row_id=obj['row_id'])
