"""
Helpers for webinar invitees
"""

import json

from flask import current_app

from app import db
from app.common.utils import calling_bigmarker_apis
from app.resources.users.models import User


def register_webinar_conference_invitee(invitee, conference_id):
    """
    When invitee register particular webinar so bigmarker conference
    regitration for particular invitee
    :param invitee:
    :param conference_id:
    :return:
    """
    response = {'status': False, 'response': {}}

    registration_obj = {}
    sub_url = 'conferences/' + 'register'

    if conference_id:
        registration_obj['id'] = conference_id
    try:
        if invitee.invitee_id:
            invited_user = User.query.filter_by(
                row_id=invitee.invitee_id).first()
            registration_obj['email'] = invited_user.email
            registration_obj['first_name'] = \
                invited_user.profile.first_name
            registration_obj['last_name'] = invited_user.profile.last_name
        else:
            registration_obj['email'] = invitee.invitee_email
            registration_obj['first_name'] = \
                invitee.invitee_first_name
            registration_obj['last_name'] = invitee.invitee_last_name

        bigmarker_response = calling_bigmarker_apis(
            sub_url=sub_url, json_data=registration_obj, method='put')
        if not bigmarker_response.ok:
            response['status'] = False
            response_content = bigmarker_response.content.decode(
                'utf8').replace("'", '"')
            response['response'] = json.loads(response_content)
            return response

        data = bigmarker_response.json()
        if 'conference_url' in data and data['conference_url']:
            invitee.conference_url = data['conference_url']
            db.session.add(invitee)
            db.session.commit()
        response['conference_url'] = data['conference_url']
        response['status'] = True
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)

    return response


def deregister_webinar_conference_invitee(invitee, conference_id=None):
    """
    When invitee delete, conference_id is passed then deregister invitee
        from webinar conference
    When invitee deregister, row_id is passed, then invitee deregister from
        webinar conference and reference to conference is deleted
        from webinar invitee model.
    """
    response = {'status': False, 'response': {}}
    registration_obj = {}

    sub_url = 'conferences/' + 'register'
    try:
        if invitee.invitee_id:
            invited_user = User.query.filter_by(
                row_id=invitee.invitee_id).first()
            registration_obj['email'] = invited_user.email
        elif invitee.invitee_email:
            registration_obj['email'] = invitee.invitee_email

        if conference_id:
            registration_obj['id'] = conference_id
            bigmarker_response = calling_bigmarker_apis(
                sub_url=sub_url, json_data=registration_obj, method='delete')

            if not bigmarker_response.ok:
                response['status'] = False
                response_content = bigmarker_response.content.decode(
                    'utf8').replace("'", '"')
                response['response'] = json.loads(response_content)
                return response
        # on deregister, delete conference related in invitee model.
        invitee.conference_url = None
        db.session.add(invitee)
        db.session.commit()
        response['status'] = True
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(e)

    return response
