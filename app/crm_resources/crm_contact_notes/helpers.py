"""
Helper classes/functions for "crm contacts note" package.
"""

from sqlalchemy import and_, or_
from flask import g

from app.resources.users.models import User
from app.crm_resources.crm_contact_notes.models import CRMContactNote
from app.crm_resources.crm_contact_notes import constants as NOTE
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_participants.models \
    import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_rsvps.models import \
    CorporateAccessEventRSVP
from app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_participants.models import WebinarParticipant
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_participants.models import WebcastParticipant
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP


def build_query_for_related_user_notes(
        created_by=None, user_id=None, query_session=None):
    """
    build query for creator and selected user related notes
    :param created_by: id of created note
    :param user_id: id of select user
    :return: query
    """
    user_email = User.query.filter_by(row_id=user_id).first().email

    query_session = query_session.filter(
        CRMContactNote.note_type != NOTE.NOTE_INDIVIDUAL,
        CRMContactNote.created_by == g.current_user['row_id'])
    # join query for corporate access event related
    ca_event_invitee_note = query_session.join(
        CorporateAccessEvent, and_(
            CorporateAccessEvent.row_id == CRMContactNote.ca_event_id,
            CorporateAccessEvent.created_by == created_by)).join(
            CorporateAccessEventInvitee, CorporateAccessEvent.row_id ==
            CorporateAccessEventInvitee.corporate_access_event_id).filter(
        or_(CorporateAccessEventInvitee.user_id == user_id,
            CorporateAccessEventInvitee.invitee_email == user_email))

    ca_event_host_note = query_session.join(
        CorporateAccessEvent, and_(
            CorporateAccessEvent.row_id == CRMContactNote.ca_event_id,
            CorporateAccessEvent.created_by == created_by)).join(
            CorporateAccessEventHost, CorporateAccessEvent.row_id ==
            CorporateAccessEventHost.corporate_access_event_id).filter(
        or_(CorporateAccessEventHost.host_email == user_email,
            CorporateAccessEventHost.host_id == user_id))

    ca_event_participant_note = query_session.join(
        CorporateAccessEvent, and_(
            CorporateAccessEvent.row_id == CRMContactNote.ca_event_id,
            CorporateAccessEvent.created_by == created_by)).join(
            CorporateAccessEventParticipant, CorporateAccessEvent.row_id ==
            CorporateAccessEventParticipant.corporate_access_event_id).filter(
        or_(CorporateAccessEventParticipant.participant_email == user_email,
            CorporateAccessEventParticipant.participant_id == user_id))

    ca_event_collaborator_note = query_session.join(
        CorporateAccessEvent, and_(
            CorporateAccessEvent.row_id == CRMContactNote.ca_event_id,
            CorporateAccessEvent.created_by == created_by)).join(
            CorporateAccessEventCollaborator, CorporateAccessEvent.row_id ==
            CorporateAccessEventCollaborator.corporate_access_event_id).filter(
            CorporateAccessEventCollaborator.collaborator_id == user_id)

    ca_event_rsvp_note = query_session.join(
        CorporateAccessEvent, and_(
            CorporateAccessEvent.row_id == CRMContactNote.ca_event_id,
            CorporateAccessEvent.created_by == created_by)).join(
            CorporateAccessEventRSVP, CorporateAccessEvent.row_id ==
            CorporateAccessEventRSVP.corporate_access_event_id).filter(
            CorporateAccessEventRSVP.email == user_email)

    # join query webinar related
    webinar_invitee = query_session.join(Webinar, and_(
        Webinar.row_id == CRMContactNote.webinar_id,
        Webinar.created_by == created_by)).join(
        WebinarInvitee, Webinar.row_id == WebinarInvitee.webinar_id).filter(
        or_(WebinarInvitee.invitee_email == user_email,
            WebinarInvitee.invitee_id == user_id))

    webinar_host = query_session.join(Webinar, and_(
        Webinar.row_id == CRMContactNote.webinar_id,
        Webinar.created_by == created_by)).join(
        WebinarHost, Webinar.row_id == WebinarHost.webinar_id).filter(
        or_(WebinarHost.host_email == user_email,
            WebinarHost.host_id == user_id))

    webinar_participant = query_session.join(Webinar, and_(
        Webinar.row_id == CRMContactNote.webinar_id,
        Webinar.created_by == created_by)).join(
        WebinarParticipant, Webinar.row_id == WebinarParticipant.webinar_id
    ).filter(or_(WebinarParticipant.participant_id == user_id,
                 WebinarParticipant.participant_email == user_email))

    webinar_rsvp = query_session.join(Webinar, and_(
        Webinar.row_id == CRMContactNote.webinar_id,
        Webinar.created_by == created_by)).join(
        WebinarRSVP, Webinar.row_id == WebinarRSVP.webinar_id).filter(
        WebinarRSVP.email == user_email)

    # join query webcast related
    webcast_invitee = query_session.join(Webcast, and_(
        Webcast.row_id == CRMContactNote.webinar_id,
        Webcast.created_by == created_by)).join(
        WebcastInvitee, Webcast.row_id == WebcastInvitee.webcast_id).filter(
        or_(WebcastInvitee.invitee_id == user_id,
            WebcastInvitee.invitee_email == user_email))

    webcast_host = query_session.join(Webcast, and_(
        Webcast.row_id == CRMContactNote.webcast_id,
        Webcast.created_by == created_by)).join(
        WebcastHost, Webcast.row_id == WebcastHost.webcast_id).filter(
        or_(WebcastHost.host_id == user_id,
            WebcastHost.host_email == user_email))

    webcast_participant = query_session.join(Webcast, and_(
        Webcast.row_id == CRMContactNote.webcast_id,
        Webcast.created_by == created_by)).join(
        WebcastParticipant, Webcast.row_id == WebcastParticipant.webcast_id
    ).filter(or_(WebcastParticipant.participant_id == user_id,
                 WebcastParticipant.participant_email == user_email))

    webcast_rsvp = query_session.join(Webcast, and_(
        Webcast.row_id == CRMContactNote.webcast_id,
        Webcast.created_by == created_by)).join(
        WebcastRSVP, Webcast.row_id == WebcastRSVP.webcast_id).filter(
        WebcastRSVP.email == user_email)

    final_query = ca_event_invitee_note.union(
        ca_event_host_note, ca_event_participant_note, ca_event_rsvp_note,
        ca_event_collaborator_note, webinar_invitee, webinar_host, webinar_rsvp,
        webinar_participant, webcast_invitee, webcast_participant, webcast_rsvp,
        webcast_host)

    return final_query
