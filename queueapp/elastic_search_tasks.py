"""
    tasks for elastic search
"""

from elasticsearch import Elasticsearch
from gevent import sleep
from sqlalchemy.orm import joinedload

from app import flaskapp, db
from app.resources.users.models import User
from app.resources.accounts.models import Account
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_collaborators.models\
    import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_participants.models\
    import CorporateAccessEventParticipant
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_rsvps.models \
    import CorporateAccessEventRSVP
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_participants.models \
    import WebinarParticipant
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP
from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_participants.models import (
    WebcastParticipant)
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP

from app.base import constants as APP

from queueapp.tasks import celery_app, logger

es = Elasticsearch([flaskapp.config['ELASTICSEARCH_URL']])


@celery_app.task(bind=True, ignore_result=True)
def update_elastic_document(self, row_id, model_name, account_id,
                            corporate_account_id, user_id, from_script,
                            *args, **kwargs):
    """
        insert related user emails in document so that only those can search
        the document.
    """

    try:
        if not from_script:
            sleep(.1)
        index = APP.DF_ES_INDEX
        doc_id = model_name + '_' + str(row_id)
        user_emails = []
        body = {'doc': {}}
        if model_name == 'CorporateAccessEvent':
            Invitee = CorporateAccessEventInvitee
            invitees = Invitee.query.join(
                User, Invitee.user_id == User.row_id,
                isouter=True).with_entities(
                Invitee.invitee_email, User.email).filter(
                Invitee.corporate_access_event_id == row_id).all()

            for invitee in invitees:
                email = invitee.email
                if not email:
                    email = invitee.invitee_email
                if email:
                    user_emails.append(email)

            Collab = CorporateAccessEventCollaborator
            collaborators = db.session.query(
                Collab.row_id.label('row_id'), User.email.label('email')
                ).join(User, Collab.collaborator_id == User.row_id).filter(
                Collab.corporate_access_event_id == row_id)

            collaborators = list(collaborators)
            for collaborator in collaborators:
                if collaborator.email:
                    user_emails.append(collaborator.email)

            Participant = CorporateAccessEventParticipant
            participants = Participant.query.join(
                User, User.row_id == Participant.participant_id,
                isouter=True).with_entities(
                User.email, Participant.participant_email).filter(
                Participant.corporate_access_event_id == row_id)

            for participant in list(participants):
                email = participant.email
                if not email:
                    email = participant.participant_email
                if email:
                    user_emails.append(email)

            Host = CorporateAccessEventHost
            hosts = Host.query.join(
                User, Host.host_id == User.row_id).with_entities(
                User.email, Host.host_email).filter(
                Host.corporate_access_event_id == row_id)

            for host in list(hosts):
                email = host.email
                if not email:
                    email = host.host_email
                if email:
                    user_emails.append(email)

            Rsvp = CorporateAccessEventRSVP
            rsvps = Rsvp.query.with_entities( Rsvp.email).filter(
                Rsvp.corporate_access_event_id == row_id)

            for rsvp in list(rsvps):
                email = rsvp.email
                if email:
                    user_emails.append(email)

        if model_name == 'Webinar':
            invitees = WebinarInvitee.query.join(
                User, WebinarInvitee.invitee_id == User.row_id,
                isouter=True).with_entities(
                WebinarInvitee.invitee_email, User.email).filter(
                WebinarInvitee.webinar_id == row_id).all()

            for invitee in invitees:
                email = invitee.email
                if not email:
                    email = invitee.invitee_email
                if email:
                    user_emails.append(email)

            Participant = WebinarParticipant
            participants = Participant.query.join(
                User, User.row_id == Participant.participant_id,
                isouter=True).with_entities(
                User.email, Participant.participant_email).filter(
                Participant.webinar_id == row_id)

            for participant in list(participants):
                email = participant.email
                if not email:
                    email = participant.participant_email
                if email:
                    user_emails.append(email)

            Host = WebinarHost
            hosts = Host.query.join(
                User, Host.host_id == User.row_id).with_entities(
                User.email, Host.host_email).filter(
                Host.webinar_id == row_id)

            for host in list(hosts):
                email = host.email
                if not email:
                    email = host.host_email
                if email:
                    user_emails.append(email)

            Rsvp = WebinarRSVP
            rsvps = Rsvp.query.with_entities(Rsvp.email).filter(
                Rsvp.webinar_id == row_id)

            for rsvp in list(rsvps):
                email = rsvp.email
                if email:
                    user_emails.append(email)

        if model_name == 'Webcast':
            invitees = WebcastInvitee.query.join(
                User, WebcastInvitee.invitee_id == User.row_id,
                isouter=True).with_entities(
                WebcastInvitee.invitee_email, User.email).filter(
                WebcastInvitee.webcast_id == row_id).all()

            for invitee in invitees:
                email = invitee.email
                if not email:
                    email = invitee.invitee_email
                if email:
                    user_emails.append(email)

            Participant = WebcastParticipant
            participants = Participant.query.join(
                User, User.row_id == Participant.participant_id,
                isouter=True).with_entities(
                User.email, Participant.participant_email).filter(
                Participant.webcast_id == row_id)

            for participant in list(participants):
                email = participant.email
                if not email:
                    email = participant.participant_email
                if email:
                    user_emails.append(email)

            Host = WebcastHost
            hosts = Host.query.join(
                User, Host.host_id == User.row_id).with_entities(
                User.email, Host.host_email).filter(
                Host.webcast_id == row_id)

            for host in list(hosts):
                email = host.email
                if not email:
                    email = host.host_email
                if email:
                    user_emails.append(email)

            Rsvp = WebcastRSVP
            rsvps = Rsvp.query.with_entities(Rsvp.email).filter(
                Rsvp.webcast_id == row_id)

            for rsvp in list(rsvps):
                email = rsvp.email
                if email:
                    user_emails.append(email)

        if user_emails:
            body['doc']['user_emails'] = user_emails

        from app.global_search.helpers import get_act_dict
        if account_id:
            account = Account.query.get(account_id)
            body['doc']['account'] = get_act_dict(account)
        if corporate_account_id:
            account = Account.query.get(corporate_account_id)
            body['doc']['corporate_account'] = get_act_dict(account)
        if user_id:
            privacy_settings = {}
            privacy_fileds = [
                'search_privacy', 'search_privacy_designation_level',
                'search_privacy_industry', 'search_privacy_sector',
                'search_privacy_market_cap_min',
                'search_privacy_market_cap_max']
            user = User.query.filter(User.row_id==user_id).options(
                joinedload(User.settings).load_only(*privacy_fileds),
                joinedload(User.profile)).first()
            privacy_settings['designation_level'] = ""
            if user.profile.designation_link:
                privacy_settings['designation_level'] = \
                    user.profile.designation_link.designation_level
            for field in privacy_fileds:
                privacy_settings[field] = getattr(user.settings, field)
            body['doc'].update(privacy_settings)

        es.update(index=index, doc_type=index, id=doc_id, body=body)

        result = True
    except Exception as e:
        logger.exception(e)
        result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def update_matched_docs(self, account_id, account_data, *args, **kwargs):
    index = APP.DF_ES_INDEX
    q = {
        "script": {
            "inline": "ctx._source.account = params.account",
            "lang": "painless",
            "params": {
                "account": account_data
            }
        },
        "query": {'term': {'account.row_id': account_id}}
    }
    es.update_by_query(body=q, doc_type=index, index=index)
