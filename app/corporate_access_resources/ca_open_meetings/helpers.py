"""
Helpers for ca open meeting
"""

from sqlalchemy.orm import load_only

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
    if json_data and 'open_to_all' in json_data and json_data['open_to_all']:
        if 'invitee_ids' in json_data:
            json_data.pop('invitee_ids')

    # remove existing participant from external participant if participant
    # exists both object(external or internal)
    participant_ids = []
    if ((json_data and 'ca_open_meeting_participants' in json_data and
            json_data['ca_open_meeting_participants'] and
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
                json_data['ca_open_meeting_participants']]

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
