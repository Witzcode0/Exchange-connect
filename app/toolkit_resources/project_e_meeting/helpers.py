"""
Helpers for webinars
"""

from datetime import timedelta
from sqlalchemy import and_, or_
from sqlalchemy.orm import load_only

from app import db
from app.common.utils import calling_bigmarker_apis
from app.toolkit_resources.project_e_meeting.models import (
    Emeeting)
from app.resources.users.models import User
from app.toolkit_resources.project_e_meeting_invitee.models import (
    EmeetingInvitee)


def pre_registration_user_for_conference(emeeting):
    """
    pre-register for host, participant and rsvp in bigmarker for particular
    conference
    :param webinar: webinar data
    :return:
    """

    if emeeting.conference_id:
        registration_obj = {}
        sub_url = 'conferences/' + 'register'
        registration_obj['id'] = emeeting.conference_id

        # for invitee
        if emeeting.e_meeting_invitees:
            for invitee in emeeting.e_meeting_invitees:
                if not invitee.conference_url:
                    if invitee.invitee_id:
                        invitee_user = User.query.filter_by(
                            row_id=invitee.invitee_id).first()
                        registration_obj['email'] = \
                            invitee_user.email
                        registration_obj['first_name'] = \
                            invitee_user.profile.first_name
                        registration_obj['last_name'] = \
                            invitee_user.profile.last_name

                    response = calling_bigmarker_apis(
                        sub_url=sub_url, json_data=registration_obj,
                        method='put')
                    if not response.ok:
                        continue
                    data = response.json()
                    # update conference_url
                    if ('conference_url' in data and
                            data['conference_url']):
                        invitee.conference_url = \
                            data['conference_url']
                        db.session.add(invitee)
            db.session.commit()

    return
