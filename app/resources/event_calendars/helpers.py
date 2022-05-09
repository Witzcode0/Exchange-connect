
import os

from flask import current_app, g
from sqlalchemy import (
    and_, or_, inspect, cast, Date, func, any_, null, BigInteger)
from sqlalchemy.orm import aliased

from app import db
from app.common.utils import get_s3_download_link, do_nothing
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.resources.event_calendars import constants as EVNTCAL
from app.resources.user_profiles.models import UserProfile
from app.resources.account_profiles.models import AccountProfile
from app.resources.accounts.models import Account
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_participants.\
    models import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_attendees.\
    models import CorporateAccessEventAttendee
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_participants.models import \
    WebinarParticipant
from app.webinar_resources.webinar_attendees.models import WebinarAttendee
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_participants.models import \
    WebcastParticipant
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)


def _build_final_query(filters, query_filters, query_session, operator, model):
    """
    Builds the actual query, when passed the "query_filters" generated in
    "_build_query" and possibly "build_query" in child (when there are
    extra args)
    """
    # build actual query
    query = query_session
    final_filter = []
    query_filters['filters'] = []
    mapper = None
    if model == EVNTCAL.CORPORATE:
        mapper = inspect(CorporateAccessEvent)
    elif model == EVNTCAL.WEBCAST:
        mapper = inspect(Webcast)
    elif model == EVNTCAL.WEBINAR:
        mapper = inspect(Webinar)
    if filters:
        for f in filters:
            # dates
            if f in ['started_at_from', 'started_at_to',
                     'ended_at_from', 'ended_at_to'] and filters[f]:
                # get actual field name
                fld = f.replace('_from', '').replace('_to', '')
                # build date query
                if '_from' in f:
                    query_filters['filters'].append(
                        mapper.columns[fld] >= filters[f])
                    continue
                if '_to' in f:
                    query_filters['filters'].append(
                        mapper.columns[fld] <= filters[f])
                    continue
            if f in ['started_at', 'ended_at'] and filters[f]:
                query_filters['filters'].append(
                    cast(mapper.columns[f], Date) == filters[f])
                continue
    aliased_account = aliased(Account)

    if query_filters['filters']:
        if operator == 'and':
            op_fxn = and_
        elif operator == 'or':
            op_fxn = or_
        final_filter.append(op_fxn(*query_filters['filters']))
    if query_filters['base']:  # base filter will always be and_
        final_filter.append(and_(*query_filters['base']))
    if final_filter:
        query = query.filter(and_(*final_filter))
    if mapper:
        domain_name = get_domain_name()
        domain_id, domain_config = get_domain_info(domain_name)
        query = query.join(
            aliased_account,
            mapper.columns['account_id'] == aliased_account.row_id).filter(
            aliased_account.blocked == False,
            aliased_account.domain_id == domain_id)

    return query


def add_logo_url(objs):
    for obj in objs:
        root_thumbnail_config = current_app.config[
            AccountProfile.root_profile_photo_folder_key]
        if obj['event_type'] == EVNTCAL.CORPORATE:
            root_config = current_app.config[
                CorporateAccessEvent.root_invite_logo_folder]
        elif obj['event_type'] == EVNTCAL.WEBCAST:
            root_config = current_app.config[
                Webcast.root_invite_logo_folder]
        elif obj['event_type'] == EVNTCAL.WEBINAR:
            root_config = current_app.config[
                Webinar.root_invite_logo_folder]

        if obj['invite_logo_filename']:
            if current_app.config['S3_UPLOAD']:
                signer = get_s3_download_link
            else:
                signer = do_nothing
            obj['invite_logo_url'] = signer(os.path.join(
                root_config, str(obj['row_id']), obj['invite_logo_filename']),
                expires_in=3600)
        if obj['profile_thumbnail']:
            if current_app.config['S3_UPLOAD']:
                thumbnail_bucket_name = current_app.config[
                    'S3_THUMBNAIL_BUCKET']
                s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
                signer = get_s3_download_link
            else:
                signer = do_nothing
            obj['profile_thumbnail_url'] = os.path.join(
                s3_url, thumbnail_bucket_name, root_thumbnail_config,
                str(obj['account']), obj['profile_thumbnail'])


def corporate_query(filters, query_filters, operator):
    """
    create final query of corporate access event with union invitee, host,
    participate, collaborator
    :param filters: filters such as started_at, ended_at etc
    :param query_filters: base or filter
    :param operator: operator such as or, and
    :return: final query
    """
    # corporate access event query
    corporate_session = db.session.query(
        CorporateAccessEvent.row_id.label('row_id'),
        CorporateAccessEvent.event_sub_type_id.label('event_type_id'),
        CorporateAccessEvent.title.label('title'),
        CorporateAccessEvent.description.label('description'),
        func.concat(EVNTCAL.CORPORATE).label('event_type'),
        CorporateAccessEvent.created_by.label('creator'),
        CorporateAccessEvent.started_at.label('start_date'),
        CorporateAccessEvent.ended_at.label('end_date'),
        CorporateAccessEvent.invite_logo_filename.label(
            'invite_logo_filename'),
        CorporateAccessEventInvitee.row_id.label('invited'),
        CorporateAccessEventCollaborator.collaborator_id.label('collaborated'),
        CorporateAccessEventParticipant.participant_id.label('participated'),
        CorporateAccessEventHost.host_id.label('hosted'),
        CorporateAccessEventAttendee.attendee_id.label('attended'),
        UserProfile.first_name.label('name'),
        Account.account_name.label('account_name'),
        Account.account_type.label('account_type'),
        AccountProfile.row_id.label('account'),
        AccountProfile.profile_thumbnail.label('profile_thumbnail'),
        CorporateAccessEvent.city.label('city'))

    main_query_session = corporate_session.join(
        UserProfile, CorporateAccessEvent.created_by ==
        UserProfile.user_id).join(
        Account, Account.row_id == CorporateAccessEvent.account_id).join(
        AccountProfile,
        AccountProfile.account_id == CorporateAccessEvent.account_id).join(
        CorporateAccessEventInvitee, and_(
            CorporateAccessEventInvitee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventInvitee.user_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventParticipant,
        and_(
            CorporateAccessEventParticipant.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventHost,
        and_(
            CorporateAccessEventHost.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventCollaborator,
        and_(
            CorporateAccessEventCollaborator.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventCollaborator.collaborator_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventAttendee,
        and_(
            CorporateAccessEventAttendee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id']), isouter=True)

    # for union query without current_user filter
    query_filters_union = {}
    query_filters_union['base'] = query_filters['base'][:]
    query_filters_union['filters'] = query_filters['filters'][:]
    query_filters_union['base'].append(
        CorporateAccessEvent.is_draft.is_(False))
    query_filters_union['base'].append(
        CorporateAccessEvent.cancelled.is_(False))

    query_filters['base'].append(or_(
        CorporateAccessEvent.created_by == g.current_user['row_id'],
        and_(g.current_user['account_type'] ==
             any_(CorporateAccessEvent.account_type_preference),
             CorporateAccessEvent.is_draft.is_(False),
             CorporateAccessEvent.open_to_all.is_(True))))
    corporate_main_query = _build_final_query(
        filters, query_filters, main_query_session, operator,
        EVNTCAL.CORPORATE)

    query_for_union = _build_final_query(
        filters, query_filters_union, corporate_session, operator,
        EVNTCAL.CORPORATE)

    # for corporate access event invited
    query_for_invited = query_for_union.join(
        UserProfile, CorporateAccessEvent.created_by ==
        UserProfile.user_id).join(
        Account, Account.row_id == CorporateAccessEvent.account_id).join(
        AccountProfile,
        AccountProfile.account_id == CorporateAccessEvent.account_id).join(
        CorporateAccessEventParticipant,
        and_(
            CorporateAccessEventParticipant.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventHost,
        and_(
            CorporateAccessEventHost.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventInvitee, and_(
            CorporateAccessEventInvitee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            or_(CorporateAccessEventInvitee.user_id == g.current_user['row_id'],
                CorporateAccessEventInvitee.invitee_email ==
                g.current_user['email'])
            )).join(
        CorporateAccessEventCollaborator,
        and_(
            CorporateAccessEventCollaborator.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventCollaborator.collaborator_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventAttendee,
        and_(
            CorporateAccessEventAttendee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id']), isouter=True)

    # for corporate access event participated
    query_for_participated = query_for_union.join(
        UserProfile, CorporateAccessEvent.created_by ==
        UserProfile.user_id).join(
        Account, Account.row_id == CorporateAccessEvent.account_id).join(
        AccountProfile,
        AccountProfile.account_id == CorporateAccessEvent.account_id).join(
        CorporateAccessEventInvitee, and_(
            CorporateAccessEventInvitee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventInvitee.user_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventHost,
        and_(
            CorporateAccessEventHost.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventParticipant, and_(
            CorporateAccessEventParticipant.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventParticipant.participant_id ==
            g.current_user['row_id'])).join(
        CorporateAccessEventCollaborator,
        and_(
            CorporateAccessEventCollaborator.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventCollaborator.collaborator_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventAttendee,
        and_(
            CorporateAccessEventAttendee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id']), isouter=True)
    # for corporate access event hosted
    query_for_hosted = query_for_union.join(
        UserProfile, CorporateAccessEvent.created_by ==
        UserProfile.user_id).join(
        Account, Account.row_id == CorporateAccessEvent.account_id).join(
        AccountProfile,
        AccountProfile.account_id == CorporateAccessEvent.account_id).join(
        CorporateAccessEventInvitee, and_(
            CorporateAccessEventInvitee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventInvitee.user_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventHost,
        and_(
            CorporateAccessEventHost.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventHost.host_id ==
            g.current_user['row_id'])).join(
        CorporateAccessEventParticipant, and_(
            CorporateAccessEventParticipant.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventCollaborator,
        and_(
            CorporateAccessEventCollaborator.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventCollaborator.collaborator_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventAttendee,
        and_(
            CorporateAccessEventAttendee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id']), isouter=True)

    # for corporate access event collaborated
    query_for_collaborated = query_for_union.join(
        UserProfile, CorporateAccessEvent.created_by ==
        UserProfile.user_id).join(
        Account, Account.row_id == CorporateAccessEvent.account_id).join(
        AccountProfile,
        AccountProfile.account_id == CorporateAccessEvent.account_id).join(
        CorporateAccessEventInvitee, and_(
            CorporateAccessEventInvitee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventInvitee.user_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventHost,
        and_(
            CorporateAccessEventHost.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventParticipant, and_(
            CorporateAccessEventParticipant.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventCollaborator,
        and_(
            CorporateAccessEventCollaborator.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventCollaborator.collaborator_id ==
            g.current_user['row_id'])).join(
        CorporateAccessEventAttendee,
        and_(
            CorporateAccessEventAttendee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id']), isouter=True)

    # for corporate access event attended
    query_for_attended = query_for_union.join(
        UserProfile, CorporateAccessEvent.created_by ==
                     UserProfile.user_id).join(
        Account, Account.row_id == CorporateAccessEvent.account_id).join(
        AccountProfile,
        AccountProfile.account_id == CorporateAccessEvent.account_id).join(
        CorporateAccessEventInvitee, and_(
            CorporateAccessEventInvitee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventInvitee.user_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventHost,
        and_(
            CorporateAccessEventHost.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventParticipant, and_(
            CorporateAccessEventParticipant.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventCollaborator,
        and_(
            CorporateAccessEventCollaborator.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventCollaborator.collaborator_id ==
            g.current_user['row_id']), isouter=True).join(
        CorporateAccessEventAttendee,
        and_(
            CorporateAccessEventAttendee.corporate_access_event_id ==
            CorporateAccessEvent.row_id,
            CorporateAccessEventAttendee.attendee_id ==
            g.current_user['row_id']))

    corporate_final_query = corporate_main_query.union(
        query_for_invited, query_for_participated,
        query_for_hosted, query_for_collaborated, query_for_attended)
    return corporate_final_query


def webinar_query(filters, query_filters, operator):
    """
    create final query of webinar with union invitee, host,
    participate, collaborator
    :param filters: filters such as started_at, ended_at etc
    :param query_filters: base or filter
    :param operator: operator such as or, and
    :return: final query
    """
    # webinar query for event calender
    webinar_session = db.session.query(
        Webinar.row_id.label('row_id'),
        Webinar.row_id.label('event_type_id'),
        Webinar.title.label('title'),
        Webinar.description.label('description'),
        func.concat(EVNTCAL.WEBINAR).label('event_type'),
        Webinar.created_by.label('creator'),
        Webinar.started_at.label('start_date'),
        Webinar.ended_at.label('end_date'),
        Webinar.invite_logo_filename.label(
            'invite_logo_filename'),
        WebinarInvitee.row_id.label('invited'),
        Webinar.row_id.label('collaborated'),
        WebinarParticipant.participant_id.label('participated'),
        WebinarHost.host_id.label('hosted'),
        WebinarAttendee.attendee_id.label('attended'),
        UserProfile.first_name.label('name'),
        Account.account_name.label('account_name'),
        Account.account_type.label('account_type'),
        AccountProfile.row_id.label('account'),
        AccountProfile.profile_thumbnail.label('profile_thumbnail'),
        # this query has been used for union with event for calender
        # which has city_id so making it "unionable".
        # also unionable is not a real word :)
        null().label('city_id'),)

    webinar_main_query_session = webinar_session.join(
        UserProfile, Webinar.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webinar.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webinar.account_id).join(
        WebinarInvitee, and_(
            WebinarInvitee.webinar_id == Webinar.row_id,
            WebinarInvitee.invitee_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarParticipant,
        and_(
            WebinarParticipant.webinar_id == Webinar.row_id,
            WebinarParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarHost,
        and_(
            WebinarHost.webinar_id == Webinar.row_id,
            WebinarHost.host_id == g.current_user['row_id']),
        isouter=True).join(
            WebinarAttendee, and_(
            WebinarAttendee.webinar_id==Webinar.row_id,
            WebinarAttendee.attendee_id==g.current_user['row_id']),
        isouter=True).filter(or_(
            Webinar.created_by == g.current_user['row_id'],
            g.current_user['account_type'] == any_(
                Webinar.open_to_account_types),
            Webinar.open_to_public.is_(True)))

    filters_with_no_cancelled = query_filters['base'][:]
    filters_with_no_cancelled.append(
        Webinar.cancelled.is_(False))

    webinar_query = _build_final_query(
        filters, query_filters, webinar_main_query_session, operator,
        EVNTCAL.WEBINAR)
    query_filters['base'] = filters_with_no_cancelled
    webinar_query_for_union = _build_final_query(
        filters, query_filters, webinar_session, operator,
        EVNTCAL.WEBINAR)
    # for corporate access event invited
    webinar_query_for_invited = webinar_query_for_union.join(
        UserProfile, Webinar.created_by == UserProfile.user_id).join(
        AccountProfile,
        AccountProfile.account_id == Webinar.account_id).join(
        Account, Account.row_id == Webinar.account_id).join(
        WebinarParticipant,
        and_(
            WebinarParticipant.webinar_id == Webinar.row_id,
            WebinarParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarHost,
        and_(
            WebinarHost.webinar_id == Webinar.row_id,
            WebinarHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarInvitee, and_(
            WebinarInvitee.webinar_id == Webinar.row_id,
            or_(WebinarInvitee.invitee_id == g.current_user['row_id'],
                WebinarInvitee.invitee_email == g.current_user['email']))).join(
            WebinarAttendee,
            and_(
                WebinarAttendee.webinar_id==Webinar.row_id,
                WebinarAttendee.attendee_id==g.current_user['row_id']),
            isouter=True)
    # for corporate access event participated
    webinar_query_for_participated = webinar_query_for_union.join(
        UserProfile, Webinar.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webinar.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webinar.account_id).join(
        WebinarParticipant,
        and_(
            WebinarParticipant.webinar_id == Webinar.row_id,
            WebinarParticipant.participant_id ==
            g.current_user['row_id'])).join(
        WebinarHost,
        and_(
            WebinarHost.webinar_id == Webinar.row_id,
            WebinarHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarInvitee, and_(
            WebinarInvitee.webinar_id == Webinar.row_id,
            WebinarInvitee.invitee_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarAttendee, and_(
            WebinarAttendee.webinar_id==Webinar.row_id,
            WebinarAttendee.attendee_id==g.current_user['row_id']),
            isouter=True)
    # for corporate access event hosted
    webinar_query_for_hosted = webinar_query_for_union.join(
        UserProfile, Webinar.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webinar.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webinar.account_id).join(
        WebinarParticipant,
        and_(
            WebinarParticipant.webinar_id == Webinar.row_id,
            WebinarParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarHost,
        and_(
            WebinarHost.webinar_id == Webinar.row_id,
            WebinarHost.host_id ==
            g.current_user['row_id'])).join(
        WebinarInvitee, and_(
            WebinarInvitee.webinar_id == Webinar.row_id,
            WebinarInvitee.invitee_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarAttendee, and_(
            WebinarAttendee.webinar_id==Webinar.row_id,
            WebinarAttendee.attendee_id==g.current_user['row_id']),
        isouter=True)
    # for corporate access event attended
    webinar_query_for_attended = webinar_query_for_union.join(
        UserProfile, Webinar.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webinar.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webinar.account_id).join(
        WebinarParticipant,
        and_(
            WebinarParticipant.webinar_id == Webinar.row_id,
            WebinarParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarHost,
        and_(
            WebinarHost.webinar_id == Webinar.row_id,
            WebinarHost.host_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarInvitee, and_(
            WebinarInvitee.webinar_id == Webinar.row_id,
            WebinarInvitee.invitee_id ==
            g.current_user['row_id']), isouter=True).join(
        WebinarAttendee, and_(
            WebinarAttendee.webinar_id == Webinar.row_id,
            WebinarAttendee.attendee_id == g.current_user['row_id']))
    webinar_final_query = webinar_query.union(
        webinar_query_for_hosted, webinar_query_for_invited,
        webinar_query_for_participated, webinar_query_for_attended)

    return webinar_final_query


def webcast_query(filters, query_filters, operator):
    """
    create final query of webcast with union invitee, host, participate
    :param filters: filters such as started_at, ended_at etc
    :param query_filters: base or filter
    :param operator: operator such as or, and
    :return: final query
    """
    # webcast query for event calender
    webcast_session = db.session.query(
        Webcast.row_id.label('row_id'),
        cast(null(), BigInteger).label('event_type_id'),
        # Webcast.row_id.label('event_type_id'),
        Webcast.title.label('title'),
        Webcast.description.label('description'),
        func.concat(EVNTCAL.WEBCAST).label('event_type'),
        Webcast.created_by.label('creator'),
        Webcast.started_at.label('start_date'),
        Webcast.ended_at.label('end_date'),
        Webcast.invite_logo_filename.label(
            'invite_logo_filename'),
        WebcastInvitee.row_id.label('invited'),
        # to make this query compatible with event calendars
        cast(null(), BigInteger).label('collaborated'),
        WebcastParticipant.row_id.label('participated'),
        WebcastHost.row_id.label('hosted'),
        # to make this query compatible with event calendars
        cast(null(), BigInteger).label('attended'),
        UserProfile.first_name.label('name'),
        Account.account_name.label('account_name'),
        Account.account_type.label('account_type'),
        AccountProfile.row_id.label('account'),
        AccountProfile.profile_thumbnail.label('profile_thumbnail'),
        # to make this query compatible with event calendars
        null().label('city'),)

    webcast_main_query_session = webcast_session.join(
        UserProfile, Webcast.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webcast.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webcast.account_id).join(
        WebcastInvitee, and_(
            WebcastInvitee.webcast_id == Webcast.row_id,
            WebcastInvitee.invitee_id ==
            g.current_user['row_id']), isouter=True).join(
        WebcastParticipant,
        and_(
            WebcastParticipant.webcast_id == Webcast.row_id,
            WebcastParticipant.participant_id ==
            g.current_user['row_id']), isouter=True).join(
        WebcastHost,
        and_(
            WebcastHost.webcast_id == Webcast.row_id,
            WebcastHost.host_id == g.current_user['row_id']),
        isouter=True).filter(
        Webcast.created_by == g.current_user['row_id'])

    filters_with_no_cancelled = query_filters['base'][:]
    filters_with_no_cancelled.append(
        Webcast.cancelled.is_(False))

    query = _build_final_query(
        filters, query_filters, webcast_main_query_session, operator,
        EVNTCAL.WEBCAST)

    query_filters['base'] = filters_with_no_cancelled
    webcast_query_for_union = _build_final_query(
        filters, query_filters, webcast_session, operator,
        EVNTCAL.WEBCAST)
    # for webcast invited
    webcast_query_for_invited = webcast_query_for_union.join(
        UserProfile, Webcast.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webcast.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webcast.account_id).join(
        WebcastParticipant,
        and_(
            WebcastParticipant.webcast_id == Webcast.row_id,
            or_(WebcastParticipant.participant_id == g.current_user['row_id'],
                WebcastParticipant.participant_email==g.current_user['email'])),
        isouter=True).join(
        WebcastHost,
        and_(
            WebcastHost.webcast_id == Webcast.row_id,
            or_(WebcastHost.host_id == g.current_user['row_id'],
                WebcastHost.host_email == g.current_user['email'])),
        isouter=True).join(
        WebcastInvitee, and_(
            WebcastInvitee.webcast_id == Webcast.row_id,
            or_(WebcastInvitee.invitee_id == g.current_user['row_id'],
                WebcastInvitee.invitee_email == g.current_user['email'])
            ))
    # for webcast participated
    webcast_query_for_participated = webcast_query_for_union.join(
        UserProfile, Webcast.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webcast.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webcast.account_id).join(
        WebcastParticipant,
        and_(
            WebcastParticipant.webcast_id == Webcast.row_id,
            or_(WebcastParticipant.participant_id == g.current_user['row_id'],
                WebcastParticipant.participant_email==g.current_user['email']))
        ).join(
        WebcastHost,
        and_(
            WebcastHost.webcast_id == Webcast.row_id,
            or_(WebcastHost.host_id == g.current_user['row_id'],
                WebcastHost.host_email == g.current_user['email'])),
        isouter=True).join(
        WebcastInvitee, and_(
            WebcastInvitee.webcast_id == Webcast.row_id,
            or_(WebcastInvitee.invitee_id == g.current_user['row_id'],
                WebcastInvitee.invitee_email == g.current_user['email'])),
        isouter=True)
    # for webcast hosted
    webcast_query_for_hosted = webcast_query_for_union.join(
        UserProfile, Webcast.created_by == UserProfile.user_id).join(
        Account, Account.row_id == Webcast.account_id).join(
        AccountProfile,
        AccountProfile.account_id == Webcast.account_id).join(
        WebcastParticipant,
        and_(
            WebcastParticipant.webcast_id == Webcast.row_id,
            or_(WebcastParticipant.participant_id == g.current_user['row_id'],
                WebcastParticipant.participant_email==g.current_user['email'])),
        isouter=True).join(
        WebcastHost,
        and_(
            WebcastHost.webcast_id == Webcast.row_id,
            or_(WebcastHost.host_id == g.current_user['row_id'],
                WebcastHost.host_email == g.current_user['email']))).join(
        WebcastInvitee, and_(
            WebcastInvitee.webcast_id == Webcast.row_id,
            or_(WebcastInvitee.invitee_id == g.current_user['row_id'],
                WebcastInvitee.invitee_email == g.current_user['email'])
            ), isouter=True)
    webcast_final_query = query.union(
        webcast_query_for_hosted, webcast_query_for_invited,
        webcast_query_for_participated)

    return webcast_final_query
