"""
Helpers for webcasts
"""

from sqlalchemy.orm import load_only

from app import db
from app.common.utils import calling_bigmarker_apis
from app.webcast_resources.webcast_participants.models import \
    WebcastParticipant
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP
from app.resources.users.models import User


def remove_unused_data(
        json_data=None, webcast_participant_data=None,
        external_participant_data=None):
    """
    remove all files related variable which come as string data such as (
    invite_logo_filename, invite_banner_filename, audio_filename,
    video_filename )
    remove external invitee, host and participant user if all ready exists in
    invitee user, host user and participant user
    :param json_data: json data
    :param webcast_participant_data: list of object of participant with
    participant id
    :param external_participant_data : list of object of participant with
    participant email
    :return: json_data after remove all files related variable as a string data
    :return external_participant_data: after remove existing participant
    """

    if json_data and 'invite_logo_filename' in json_data:
        json_data.pop('invite_logo_filename')
    if json_data and 'invite_banner_filename' in json_data:
        json_data.pop('invite_banner_filename')
    if json_data and 'audio_filename' in json_data:
        json_data.pop('audio_filename')
    if json_data and 'video_filename' in json_data:
        json_data.pop('video_filename')

    if (json_data and 'host_ids' in json_data and json_data['host_ids'] and
            '' not in json_data['host_ids'] and
            'external_hosts' in json_data and json_data['external_hosts']):
        host_email_ids = [usr.email for usr in User.query.filter(
            User.row_id.in_(json_data['host_ids'])).options(
            load_only('row_id', 'email')).all()]
        for ext_host in json_data['external_hosts']:
            if ext_host['host_email'] in host_email_ids:
                json_data['external_hosts'].remove(ext_host)

    if (json_data and 'invitee_ids' in json_data and
            '' not in json_data['invitee_ids'] and
            json_data['invitee_ids'] and 'external_invitees' in json_data and
            json_data['external_invitees']):
        invitee_email_ids = [usr.email for usr in User.query.filter(
            User.row_id.in_(json_data['invitee_ids'])).options(
            load_only('row_id', 'email')).all()]
        for ext_invitee in json_data['external_invitees']:
            if ext_invitee['invitee_email'] in invitee_email_ids:
                json_data['external_invitees'].remove(ext_invitee)

    # remove existing participant from external participant if participant
    # exists both object(external or internal)
    participant_ids = []
    if ((json_data and 'webcast_participants' in json_data and
            json_data['webcast_participants'] and
            'external_participants' in json_data and
            json_data['external_participants']) or (
            webcast_participant_data and external_participant_data)):
        if webcast_participant_data:
            participant_ids = [
                participate['participant_id'] for participate in
                webcast_participant_data]
        else:
            participant_ids = [
                participate['participant_id'] for participate in
                json_data['webcast_participants']]

        if external_participant_data:
            invitee_email_ids = [usr.email for usr in User.query.filter(
                User.row_id.in_(participant_ids)).options(
                load_only('row_id', 'email')).all()]
            for ext_participant in external_participant_data:
                if ext_participant['participant_email'] in invitee_email_ids:
                    external_participant_data.remove(ext_participant)
        else:
            invitee_email_ids = [usr.email for usr in User.query.filter(
                User.row_id.in_(participant_ids)).options(
                load_only('row_id', 'email')).all()]
            for ext_participant in json_data['external_participants']:
                if ext_participant['participant_email'] in invitee_email_ids:
                    json_data['external_participants'].remove(ext_participant)

    return json_data, external_participant_data


def remove_participant_or_rsvp_sequence_id(
        webcast_participant_data=None, external_participant_data=None,
        rsvps=None):
    """
    When sequence id change then first remove sequence id for
    particular webcast participants or rsvps
    :param webcast_participant_data: data of system user
    :param external_participant_data: data of guest user
    :param rsvps: data of webcast rsvp
    :return:
    """

    if webcast_participant_data:
        for web_pcpt in webcast_participant_data:
            if 'row_id' in web_pcpt:
                WebcastParticipant.query.filter(
                    WebcastParticipant.row_id == web_pcpt['row_id']
                ).update({WebcastParticipant.sequence_id: None},
                         synchronize_session=False)

    if external_participant_data:
        for web_pcpt in external_participant_data:
            if 'row_id' in web_pcpt:
                WebcastParticipant.query.filter(
                    WebcastParticipant.row_id == web_pcpt['row_id']
                ).update({WebcastParticipant.sequence_id: None},
                         synchronize_session=False)

    if rsvps:
        for rsvp in rsvps:
            if 'row_id' in rsvp:
                WebcastRSVP.query.filter(
                    WebcastRSVP.row_id == rsvp['row_id']).update(
                    {WebcastRSVP.sequence_id: None}, synchronize_session=False)


def check_external_invitee_exists_in_user(invitee_email):
    """
    check external invitee exists in system user or not
    :param invitee_email: external invitee email
    :return user_row_id: if external invitee email exists in system user
    return user row_id
    """
    user_row_id = None
    if invitee_email:
        user_data = User.query.filter(
            User.email == invitee_email).options(load_only('row_id')).first()
        if user_data:
            user_row_id = user_data.row_id
    return user_row_id


def pre_registration_user_for_conference(webcast):
    """
    pre-register for host, participant and rsvp in bigmarker for particular
    conference
    :param webcast: webcast data
    :return:
    """

    if webcast.conference_id:
        registration_obj = {}
        sub_url = 'conferences/' + 'register'
        registration_obj['id'] = webcast.conference_id
        # for host
        if webcast.webcast_hosts:
            for host in webcast.webcast_hosts:
                if not host.conference_url:
                    if host.host_id:
                        hosted_user = User.query.filter_by(
                            row_id=host.host_id).first()
                        registration_obj['email'] = hosted_user.email
                        registration_obj['first_name'] = \
                            hosted_user.profile.first_name
                        registration_obj['last_name'] = \
                            hosted_user.profile.last_name
                    else:
                        registration_obj['email'] = host.host_email
                        registration_obj['first_name'] = \
                            host.host_first_name
                        registration_obj[
                            'last_name'] = host.host_last_name

                    response = calling_bigmarker_apis(
                        sub_url=sub_url, json_data=registration_obj,
                        method='put')
                    if not response.ok:
                        continue
                    data = response.json()
                    # update conference_url
                    if ('conference_url' in data and
                            data['conference_url']):
                        host.conference_url = data['conference_url']
                        db.session.add(host)
            db.session.commit()
        # for participant
        if webcast.webcast_participants:
            for participant in webcast.webcast_participants:
                if not participant.conference_url:
                    if participant.participant_id:
                        participant_user = User.query.filter_by(
                            row_id=participant.participant_id).first()
                        registration_obj['email'] = \
                            participant_user.email
                        registration_obj['first_name'] = \
                            participant_user.profile.first_name
                        registration_obj['last_name'] = \
                            participant_user.profile.last_name
                    else:
                        registration_obj['email'] = \
                            participant.participant_email
                        registration_obj['first_name'] = \
                            participant.participant_first_name
                        registration_obj['last_name'] = \
                            participant.participant_last_name

                    response = calling_bigmarker_apis(
                        sub_url=sub_url, json_data=registration_obj,
                        method='put')
                    if not response.ok:
                        continue
                    data = response.json()
                    # update conference_url
                    if ('conference_url' in data and
                            data['conference_url']):
                        participant.conference_url = \
                            data['conference_url']
                        db.session.add(participant)
            db.session.commit()
        # for rsvps
        if webcast.rsvps:
            for rsvp in webcast.rsvps:
                if not rsvp.conference_url:
                    registration_obj['email'] = \
                        rsvp.email
                    registration_obj['first_name'] = \
                        rsvp.contact_person
                    registration_obj['last_name'] = ''

                    response = calling_bigmarker_apis(
                        sub_url=sub_url, json_data=registration_obj,
                        method='put')
                    if not response.ok:
                        continue
                    data = response.json()
                    # update conference_url
                    if ('conference_url' in data and
                            data['conference_url']):
                        rsvp.conference_url = data['conference_url']
                        db.session.add(rsvp)
            db.session.commit()
    return
