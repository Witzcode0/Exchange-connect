"""
Request related tasks, for webinars
"""

from datetime import datetime as dt

import requests

from flask import current_app
from sqlalchemy import or_, and_

from app import db
from app.common.utils import time_converter
from app.common.helpers import generate_event_book_email_link
from app.resources.users.models import User
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_attendees.models import WebinarAttendee
from app.webinar_resources.webinar_attendees.schemas import (
    WebinarAttendeeSchema)

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def add_update_webinar_conference(self, result, row_id, *args, **kwargs):
    """
    call bigmarker third party api.
    create conference by adding conference_id and urls to db.
    update conference if exists by check with conference_id.
    generate admin url for admin access.

    REQUEST_URL = 'https://www.bigmarker.com/api/v1/' (check in config)

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the webinar
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            started_at = dt.strftime(
                time_converter(webinar.started_at), '%Y-%m-%d %H:%M')
            duration = webinar.ended_at - webinar.started_at
            duration_minutes = str(int(duration.total_seconds() / 60))
            exit_url = generate_event_book_email_link(
                current_app.config['WEBINAR_EVENT_JOIN_ADD_URL'],
                webinar)
            url = current_app.config['BIGMARKER_REQUEST_URL'] + 'conferences/'
            headers = {'content-type': 'application/json',
                       'API-KEY': current_app.config['BIGMARKER_API_KEY']}
            payload = {
                'channel_id': current_app.config['BIGMARKER_CHANNEL_ID'],
                'title': webinar.title,
                'start_time': str(started_at),
                'purpose': webinar.description,
                'duration_minutes': duration_minutes,
                'exit_url': exit_url,
                'time_zone': 'Mumbai',
                'privacy': 'private',
                'schedule_type': 'one_time',
                'enable_knock_to_enter': False,
                'send_reminder_emails_to_presenters': False,
                'registration_conf_emails': False,
                'send_cancellation_email': False,
                'show_reviews': False,
                'review_emails': False,
                'poll_results': False,
                'enable_ie_safari': True,
                'enable_twitter': False,
                'auto_invite_all_channel_members': False,
                'who_can_watch_recording': 'channel_admin_only',
                'registration_required_to_view_recording': False}
            if webinar.conference_id:
                payload.pop('channel_id', None)
                payload['conference_id'] = webinar.conference_id
                url = url + webinar.conference_id
                response = requests.put(url, json=payload, headers=headers)
            else:
                response = requests.post(url, json=payload, headers=headers)
            data = response.json()
            admin_object = {}
            if 'id' in data and data['id']:
                conference_id = data['id']
                webinar.conference_id = conference_id
                admin_object['conference_id'] = conference_id
            if 'conference_address' in data and data['conference_address']:
                webinar.url = data['conference_address']
            if 'presenters' in data and data['presenters']:
                for presenter in data['presenters']:
                    if presenter['presenter_url']:
                        webinar.presenter_url = presenter['presenter_url']
                    if 'member_id' in presenter and presenter['member_id']:
                        member_id = presenter['member_id']
                        admin_object['bmid'] = member_id
            # call admin api for admin url
            if admin_object:
                admin_url = (
                    current_app.config['BIGMARKER_REQUEST_URL'] +
                    'conferences/' + admin_object['conference_id'] +
                    '/admin_url' + '?bmid=' + admin_object['bmid'])
                admin_response = requests.get(
                    admin_url, headers=headers)
                admin_data = admin_response.json()
                if 'admin_url' in admin_data and admin_data['admin_url']:
                    webinar.admin_url = admin_data['admin_url']
            db.session.add(webinar)
            db.session.commit()
            # pre-register for host, participant and rsvp in bigmarker
            # for particular conference
            if webinar.conference_id:
                registration_obj = {}
                registration_url = (
                    current_app.config['BIGMARKER_REQUEST_URL'] +
                    'conferences/' + 'register')
                registration_obj['id'] = webinar.conference_id
                # for host
                if webinar.webinar_hosts:
                    for host in webinar.webinar_hosts:
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

                            response = requests.put(
                                registration_url, json=registration_obj,
                                headers=headers)
                            data = response.json()
                            # update conference_url
                            if ('conference_url' in data and
                                    data['conference_url']):
                                host.conference_url = data['conference_url']
                                db.session.add(host)
                    db.session.commit()
                # for participant
                if webinar.webinar_participants:
                    for participant in webinar.webinar_participants:
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

                            response = requests.put(
                                registration_url, json=registration_obj,
                                headers=headers)
                            data = response.json()
                            # update conference_url
                            if ('conference_url' in data and
                                    data['conference_url']):
                                participant.conference_url = \
                                    data['conference_url']
                                db.session.add(participant)
                    db.session.commit()
                # for rsvps
                if webinar.rsvps:
                    for rsvp in webinar.rsvps:
                        if not rsvp.conference_url:
                            registration_obj['email'] = \
                                rsvp.email
                            registration_obj['first_name'] = \
                                rsvp.contact_person
                            registration_obj['last_name'] = ''

                            response = requests.put(
                                registration_url, json=registration_obj,
                                headers=headers)
                            data = response.json()
                            # update conference_url
                            if ('conference_url' in data and
                                    data['conference_url']):
                                rsvp.conference_url = data['conference_url']
                                db.session.add(rsvp)
                    db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def delete_webinar_conference(
        self, result, conference_id=None, row_id=None, *args, **kwargs):
    """
    When webinar delete, conference_id is passed then conference is deleted.
    When webinar cancel, row_id is passed then reference to
        conference is also deleted from webinar model along with conference.
    :param self:
    :param result:
    :param conference_id: conference_id of bigmarker
    :param row_id: row_id of webinar
    :param args:
    :param kwargs:
    :return:
    """
    if result:
        try:
            headers = {'content-type': 'application/json',
                       'API-KEY': current_app.config['BIGMARKER_API_KEY']}
            if row_id:
                webinar = Webinar.query.get(row_id)
                if webinar is None:
                    logger.exception('Webinar does not exist')
                    return False
                conference_id = webinar.conference_id
                # if webinar cancelled, then related fields will be Null
                webinar.conference_id, webinar.url = None, None
                webinar.presenter_url, webinar.admin_url = None, None
                db.session.add(webinar)
                db.session.commit()
            url = (current_app.config['BIGMARKER_REQUEST_URL'] +
                   'conferences/' + conference_id)
            data = requests.delete(url, headers=headers)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def register_webinar_conference_invitee(
        self, result, invitee_id, conference_id, *args, **kwargs):
    """
    When invitee register particular webinar so bigmarker conference
    regitration for particular invitee
    :param self:
    :param result:
    :param invitee_id:
    :param conference_id:
    :param args:
    :param kwargs:
    :return:
    """

    if result:
        try:
            registration_obj = {}
            invitee_data = WebinarInvitee.query.get(invitee_id)
            if invitee_data is None:
                logger.exception('Webinar invitee does not exist')
                return False
            registration_url = (current_app.config['BIGMARKER_REQUEST_URL'] +
                                'conferences/' + 'register')
            headers = {'content-type': 'application/json',
                       'API-KEY': current_app.config['BIGMARKER_API_KEY']}
            if conference_id:
                registration_obj['id'] = conference_id

            if invitee_data.invitee_id:
                invited_user = User.query.filter_by(
                    row_id=invitee_data.invitee_id).first()
                registration_obj['email'] = invited_user.email
                registration_obj['first_name'] = \
                    invited_user.profile.first_name
                registration_obj['last_name'] = invited_user.profile.last_name
            else:
                registration_obj['email'] = invitee_data.invitee_email
                registration_obj['first_name'] = \
                    invitee_data.invitee_first_name
                registration_obj['last_name'] = invitee_data.invitee_last_name

            response = requests.put(
                registration_url, json=registration_obj, headers=headers)
            data = response.json()
            if 'conference_url' in data and data['conference_url']:
                invitee_data.conference_url = data['conference_url']
                db.session.add(invitee_data)
                db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def deregister_webinar_conference_invitee(
        self, result, invitee_id, invitee_email, conference_id=None,
        row_id=None, *args, **kwargs):
    """
    When invitee delete, conference_id is passed then deregister invitee
        from webinar conference
    When invitee deregister, row_id is passed, then invitee deregister from
        webinar conference and reference to conference is deleted
        from webinar invitee model.
    :param self:
    :param result:
    :param invitee_id: id of internal invitee(system user)
    :param invitee_email: email of external invitee
    :param conference_id: id of bigmarker conference
    :param row_id: row_id of webinar invitee
    :param args:
    :param kwargs:
    :return:
    """

    if result:
        try:
            registration_obj = {}

            registration_url = (current_app.config['BIGMARKER_REQUEST_URL'] +
                                'conferences/' + 'register')
            headers = {'content-type': 'application/json',
                       'API-KEY': current_app.config['BIGMARKER_API_KEY']}
            if invitee_id:
                invited_user = User.query.filter_by(
                    row_id=invitee_id).first()
                registration_obj['email'] = invited_user.email
            elif invitee_email:
                registration_obj['email'] = invitee_email

            if row_id:
                invitee = WebinarInvitee.query.get(row_id)
                if invitee is None:
                    logger.exception('Webinar Invitee does not exist')
                    return False
                conference_id = invitee.webinar.conference_id
                # on deregister, delete conference related in invitee model.
                invitee.conference_url = None
                db.session.add(invitee)
                db.session.commit()
            if conference_id:
                registration_obj['id'] = conference_id
            response = requests.delete(
                registration_url, json=registration_obj, headers=headers)
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def get_webinar_conference_attendees_list(
        self, result, row_id, *args, **kwargs):
    """
    get conference attendee list from third party api, then store the data

    URL: https://www.bigmarker.com/api/v1/conferences/conference_id/attendees

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the webinar
    """
    if result:
        try:
            webinar = Webinar.query.get(row_id)
            if webinar is None:
                logger.exception('Webinar does not exist')
                return False
            url = (current_app.config['BIGMARKER_REQUEST_URL'] +
                   'conferences/' + webinar.conference_id + '/attendees')
            headers = {'content-type': 'application/json',
                       'API-KEY': current_app.config['BIGMARKER_API_KEY']}
            response = requests.get(url, headers=headers)
            data = response.json()
            if 'attendees' in data and data['attendees']:
                for attn in data['attendees']:
                    invitee_id = None
                    invitee = None
                    user = User.query.filter(
                        User.email == attn['email']).first()
                    if user:
                        invitee = WebinarInvitee.query.filter(and_(
                            WebinarInvitee.webinar_id == webinar.row_id,
                            WebinarInvitee.invitee_id == user.row_id)).first()
                    else:
                        invitee = WebinarInvitee.query.filter(and_(
                            WebinarInvitee.webinar_id == webinar.row_id,
                            WebinarInvitee.invitee_email == attn['email'])
                        ).first()
                    if invitee:
                        invitee_id = invitee.invitee_id
                    # create attandee_json
                    attandee_json = {'webinar_id': webinar.row_id,
                                     'attendee_id': invitee_id,
                                     'attendee_email': attn['email'],
                                     'attendee_first_name': attn['first_name'],
                                     'attendee_last_name': attn['last_name'],
                                     'created_by': webinar.created_by,
                                     'updated_by': webinar.created_by,
                                     'entered_at': attn['entered_at'],
                                     'leaved_at': attn['leaved_at'],
                                     'total_duration': attn['total_duration'],
                                     'engaged_duration': attn[
                                         'engaged_duration'],
                                     'chats_count': attn['chats_count'],
                                     'qas_count': attn['qas_count'],
                                     'polls_count': attn['polls_count'],
                                     'polls': attn['polls'],
                                     'questions': attn['questions'],
                                     'handouts': attn['handouts'],
                                     'browser_name': attn['browser_name'],
                                     'browser_version': attn[
                                         'browser_version'],
                                     'device_name': attn['device_name']}
                    attendee = WebinarAttendee.query.filter(and_(
                        WebinarAttendee.webinar_id == webinar.row_id,
                        WebinarAttendee.attendee_email == attn['email'])
                    ).first()
                    if attendee:
                        attandee_data, errors = WebinarAttendeeSchema().load(
                            attandee_json, instance=attendee, partial=True)
                        if errors:
                            logger.exception(errors)
                            continue
                        db.session.add(attandee_data)
                    else:
                        attandee_data, errors = WebinarAttendeeSchema().load(
                            attandee_json)
                        if errors:
                            logger.exception(errors)
                            continue
                        attandee_data.created_by = webinar.created_by
                        attandee_data.updated_by = webinar.created_by
                        db.session.add(attandee_data)

                db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result
