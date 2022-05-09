"""
Helpers for corporate access event
"""

from sqlalchemy.orm import load_only

from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_rsvps.models \
    import CorporateAccessEventRSVP
from app.corporate_access_resources.ref_event_types.models import \
    CARefEventType
from app.resources.users.models import User


def remove_unused_data(
        json_data=None, cae_participant_data=None,
        external_participant_data=None):
    """
    remove all files related variable which come as string data such as (
    invite_logo_filename, invite_banner_filename, audio_filename,
    video_filename )
    remove external invitee, host and participant user if all ready exists in
    invitee user, host user and participant user
    :param json_data: json data
    :param cae_participant_data: list of object of participant with
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
    # remove unused data, when meeting type event
    if (json_data and 'event_type_id' in json_data and
            json_data['event_type_id']):
        event_type = CARefEventType.query.get(json_data['event_type_id'])
        if event_type.is_meeting:
            if 'external_invitees' in json_data:
                json_data.pop('external_invitees')
            if 'host_ids' in json_data:
                json_data.pop('host_ids')
            if 'external_hosts' in json_data:
                json_data.pop('external_hosts')
            if 'corporate_access_event_participants' in json_data:
                json_data.pop('corporate_access_event_participants')
            if 'external_participants' in json_data:
                json_data.pop('external_participants')
            if 'rsvps' in json_data:
                json_data.pop('rsvps')
            if 'collaborators' in json_data:
                json_data.pop('collaborators')

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
    if ((json_data and 'corporate_access_event_participants' in json_data and
            json_data['corporate_access_event_participants'] and
            'external_participants' in json_data and
            json_data['external_participants']) or (
            cae_participant_data and external_participant_data)):
        if cae_participant_data:
            participant_ids = [
                participate['participant_id'] for participate in
                cae_participant_data]
        else:
            participant_ids = [
                participate['participant_id'] for participate in
                json_data['corporate_access_event_participants']]

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
        cae_participant_data=None, external_participant_data=None,
        rsvps=None):
    """
    When sequence id change then first remove sequence id for
    particular CAEvent participants or rsvps
    :param cae_participant_data: data of system user
    :param external_participant_data: data of guest user
    :param rsvps: data of CAEvent rsvp
    """

    if cae_participant_data:
        for cae_pcpt in cae_participant_data:
            if 'row_id' in cae_pcpt:
                CorporateAccessEventParticipant.query.filter(
                    CorporateAccessEventParticipant.row_id ==
                    cae_pcpt['row_id']).update(
                    {CorporateAccessEventParticipant.sequence_id: None},
                    synchronize_session=False)

    if external_participant_data:
        for cae_pcpt in external_participant_data:
            if 'row_id' in cae_pcpt:
                CorporateAccessEventParticipant.query.filter(
                    CorporateAccessEventParticipant.row_id ==
                    cae_pcpt['row_id']).update(
                    {CorporateAccessEventParticipant.sequence_id: None},
                    synchronize_session=False)

    if rsvps:
        for rsvp in rsvps:
            if 'row_id' in rsvp:
                CorporateAccessEventRSVP.query.filter(
                    CorporateAccessEventRSVP.row_id == rsvp['row_id']
                ).update({CorporateAccessEventRSVP.sequence_id: None},
                         synchronize_session=False)


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
