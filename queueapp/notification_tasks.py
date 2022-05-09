"""
Notification related tasks, for each type of notification
"""

from flask import current_app
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy import and_

from app import db, sockio
from app.common.utils import push_notification
from app.resources.contact_requests.models import ContactRequest
from app.resources.notifications.schemas import NotificationSchema
from app.resources.post_comments.models import PostComment
from app.resources.post_stars.models import PostStar
from app.resources.follows.models import CFollow
from app.resources.users.models import User
from app.resources.events.models import Event
from app.resources.event_invites.models import EventInvite
from app.survey_resources.survey_responses.models import SurveyResponse
from app.resources.admin_publish_notifications.models import \
    AdminPublishNotification
from app.resources.accounts.models import Account

from app.resources.notifications import constants as NOTIFY

from queueapp.tasks import celery_app, logger

from socketapp.base import constants as SOCKETAPP


@celery_app.task(bind=True, ignore_result=True)
def add_contact_request_notification(self, result, row_ids, sub_types,
                                     *args, **kwargs):
    """
    Adds a notification for a contact request.
    Notifies the related user, by checking contact request status

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the contact request
    :param sub_type:
        the sub_type of the contact request
    """

    if result:
        try:
            if not isinstance(row_ids,list):
                row_ids = [row_ids]
                sub_types = [sub_types]

            for row_id, sub_type in zip(row_ids, sub_types):
                json_data = {}
                message_name = {}
                redirect_row_id = None
                contact_request_data = ContactRequest.query.filter(
                    ContactRequest.row_id == row_id).options(joinedload(
                        ContactRequest.sendee), joinedload(
                        ContactRequest.sender)).first()

                if not contact_request_data:
                    continue
                if sub_type == NOTIFY.NT_CONTACT_REQ_REJECTED:
                    continue
                if sub_type == NOTIFY.NT_CONTACT_REQ_RECEIVED:
                    json_data['user_id'] = contact_request_data.sent_to
                    message_name['first_name'] = \
                        contact_request_data.sender.profile.first_name
                    message_name['last_name'] = \
                        contact_request_data.sender.profile.last_name
                    redirect_row_id = contact_request_data.sent_by
                else:
                    json_data['user_id'] = contact_request_data.sent_by
                    message_name['first_name'] = \
                        contact_request_data.sendee.profile.first_name
                    message_name['last_name'] = \
                        contact_request_data.sendee.profile.last_name
                    redirect_row_id = contact_request_data.sent_to
                json_data['account_id'] = contact_request_data.sendee.account_id
                json_data['notification_group'] = NOTIFY.NGT_CONTACT
                json_data['notification_type'] = sub_type
                json_data['contact_request_id'] = row_id

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    continue
                db.session.add(data)
                db.session.commit()
                # emit notification to user
                notify_user = User.query.get(data.user_id)
                # ncnt = notify_user.current_notification_count
                # User.query.filter(User.row_id == data.user_id).\
                #     update({User.current_notification_count: ncnt + 1})
                # # notify_user.current_notification_count += 1
                # db.session.add(notify_user)
                # notification count for particular user
                notify_user.current_notification_count += 1
                db.session.add(notify_user)
                db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_CONTACT,
                    'notification_type': sub_type},
                    namespace=SOCKETAPP.NS_NOTIFICATION,
                    room=notify_user.get_room_id(
                        room_type=SOCKETAPP.NS_NOTIFICATION))
                # send push notification for user
                if (notify_user.settings.android_request_device_ids or
                        notify_user.settings.ios_request_device_ids):
                    data = {
                     "content_available": True,
                     "priority": "high",
                     "show_in_foreground": True,
                     "data": {
                         "body": NOTIFY.NOTIFICATION_MESSAGES[
                                 sub_type] % message_name,
                         "title": current_app.config['BRAND_NAME'],
                         "user_id": data.user_id,
                         "notification_row_id": data.row_id,
                         "redirect_row_id": redirect_row_id,
                         "notification_group": NOTIFY.NGT_CONTACT,
                         "notification_type": sub_type,
                         "sound": "default",
                         "click_action": "FCM_PLUGIN_ACTIVITY",
                         "icon": "icon"
                     }
                    }
                    if notify_user.settings.android_request_device_ids:
                        data['registration_ids'] = notify_user.settings.\
                            android_request_device_ids
                        android_response = push_notification(data)
                    if notify_user.settings.ios_request_device_ids:
                        data['registration_ids'] = notify_user.settings. \
                            ios_request_device_ids
                        data['notification'] = {
                            "body": data['data']['body'],
                            "title": data['data']['title']}
                        ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_follow_notification(self, result, row_id, *args, **kwargs):
    """
    Adds a notification for a follow.
    Notifies the followed corporate user, by checking c_follow model.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the c_follow
    """

    if result:
        try:
            json_data = {}
            message_name = {}
            cfollow_data = CFollow.query.get(row_id)

            if not cfollow_data:
                return True
            message_name['first_name'] = cfollow_data.follower.profile.\
                first_name
            message_name['last_name'] = cfollow_data.follower.profile. \
                last_name
            company_all_user_data = User.query.filter(and_(
                User.account_id == cfollow_data.company_id,
                User.is_admin)).options(
                load_only('row_id', 'account_id')).all()

            if not company_all_user_data:
                return True

            for user_data in company_all_user_data:
                json_data['user_id'] = user_data.row_id
                json_data['account_id'] = cfollow_data.company_id
                json_data['notification_group'] = NOTIFY.NGT_GENERAL
                json_data['notification_type'] = NOTIFY.NT_GENERAL_FOLLOWED
                json_data['cfollow_id'] = row_id

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True
                db.session.add(data)
                db.session.commit()

                # emit notification to user
                notify_user = User.query.get(data.user_id)
                # ncnt = notify_user.current_notification_count
                # User.query.filter(User.row_id == data.user_id). \
                #     update({User.current_notification_count: ncnt + 1})
                # notification count for particular user
                notify_user.current_notification_count += 1
                db.session.add(notify_user)
                db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_GENERAL,
                    'notification_type': NOTIFY.NT_GENERAL_FOLLOWED},
                    namespace=SOCKETAPP.NS_NOTIFICATION,
                    room=notify_user.get_room_id(
                        room_type=SOCKETAPP.NS_NOTIFICATION))
                # send push notification for user
                if (notify_user.settings.android_request_device_ids or
                        notify_user.settings.ios_request_device_ids):
                    data = {
                        "content_available": True,
                        "priority": "high",
                        "show_in_foreground": True,
                        "data": {
                            "body": NOTIFY.
                            NOTIFICATION_MESSAGES[NOTIFY.NT_GENERAL_FOLLOWED] %
                            message_name,
                            "title": current_app.config['BRAND_NAME'],
                            "user_id": data.user_id,
                            "notification_row_id": data.row_id,
                            "redirect_row_id": cfollow_data.sent_by,
                            "notification_group": NOTIFY.NGT_GENERAL,
                            "notification_type": NOTIFY.NT_GENERAL_FOLLOWED,
                            "sound": "default",
                            "click_action": "FCM_PLUGIN_ACTIVITY",
                            "icon": "icon"
                        }
                    }
                    if notify_user.settings.android_request_device_ids:
                        data['registration_ids'] = notify_user.settings. \
                            android_request_device_ids
                        android_response = push_notification(data)
                    if notify_user.settings.ios_request_device_ids:
                        data['registration_ids'] = notify_user.settings. \
                            ios_request_device_ids
                        data['notification'] = {
                            "body": data['data']['body'],
                            "title": data['data']['title']}
                        ios_response = push_notification(data)

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_event_invite_notifications(self, result, row_id, invitee_ids, sub_type,
                                   *args, **kwargs):
    """
    Adds a notification for each invited user.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the event
    """

    if result:
        try:
            json_data = {}
            event_invite_data = EventInvite.query.filter(
                EventInvite.event_id == row_id).options(load_only(
                    'row_id', 'event_id')).first()
            if not event_invite_data:
                return True

            if not invitee_ids:
                return True

            event_participants_data = User.query.filter(
                User.row_id.in_(invitee_ids)).options(load_only(
                    'row_id', 'account_id')).all()
            if event_participants_data:
                for event_participant in event_participants_data:
                    json_data['user_id'] = event_participant.row_id
                    json_data['account_id'] = event_participant.account_id
                    json_data['notification_group'] = NOTIFY.NGT_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['event_invite_request_id'] = \
                        event_invite_data.row_id

                    data, errors = NotificationSchema().load(json_data)
                    if errors:
                        return True
                    db.session.add(data)
                    db.session.commit()

                    # emit notification to user
                    notify_user = User.query.get(data.user_id)
                    # ncnt = notify_user.current_notification_count
                    # User.query.filter(User.row_id == data.user_id). \
                    #     update({User.current_notification_count: ncnt + 1})
                    # notification count for particular user
                    notify_user.current_notification_count += 1
                    db.session.add(notify_user)
                    db.session.commit()
                    sockio.emit('new_notification', {
                        'user_id': data.user_id,
                        'notification_row_id': data.row_id,
                        'notification_group': NOTIFY.NGT_EVENT,
                        'notification_type': sub_type},
                        namespace=SOCKETAPP.NS_NOTIFICATION,
                        room=notify_user.get_room_id(
                            room_type=SOCKETAPP.NS_NOTIFICATION))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_event_creator_notification(self, result, row_id, invitee_ids, sub_type,
                                   *args, **kwargs):
    """
    Adds a notification for event creator user.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the event
    """
    if result:
        try:
            json_data = {}
            event_data = Event.query.filter(Event.row_id == row_id).first()
            if not event_data:
                return True

            if not invitee_ids:
                return True
            user_data = User.query.filter(
                User.row_id == event_data.created_by).options(load_only(
                    'row_id', 'account_id')).first()
            if user_data:
                json_data['user_id'] = user_data.row_id
                json_data['account_id'] = user_data.account_id
                json_data['notification_group'] = NOTIFY.NGT_EVENT
                json_data['notification_type'] = sub_type
                json_data['event_invite_request_id'] = \
                    invitee_ids[0]

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True
                db.session.add(data)
                db.session.commit()
                # emit notification to user
                notify_user = User.query.get(data.user_id)
                # notification count for particular user
                # ncnt = notify_user.current_notification_count
                # User.query.filter(User.row_id == data.user_id). \
                #     update({User.current_notification_count: ncnt + 1})
                # notification count for particular user
                notify_user.current_notification_count += 1
                db.session.add(notify_user)
                db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_EVENT,
                    'notification_type': sub_type},
                    namespace=SOCKETAPP.NS_NOTIFICATION,
                    room=notify_user.get_room_id(
                    room_type=SOCKETAPP.NS_NOTIFICATION))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_post_comment_notifications(self, result, row_id, *args, **kwargs):
    """
    Adds a notification for post
    Notifies the post created user and post commented users

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the event
    """

    if result:
        try:
            json_data = {}
            post_comment = PostComment.query.filter(
                PostComment.row_id == row_id).options(joinedload(
                    PostComment.post).load_only('created_by', 'account_id'),
                    joinedload(PostComment.post_commented)).first()
            if not post_comment:
                return True

            # add notification for post comment creator when reply
            if post_comment.in_reply_to:
                json_data['user_id'] =\
                    post_comment.post_commented.creator.row_id
                json_data['account_id'] =\
                    post_comment.post_commented.account.row_id
                json_data['notification_group'] = NOTIFY.NGT_GENERAL
                json_data['notification_type'] = NOTIFY.NT_GENERAL_COMMENTED
                json_data['post_id'] = post_comment.post_id
                json_data['post_comment_id'] = row_id

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True
                db.session.add(data)

            # add notification for post creator
            if post_comment.post.created_by != kwargs['log_uid']:
                json_data['user_id'] = post_comment.post.created_by
                json_data['account_id'] = post_comment.post.account_id
                json_data['notification_group'] = NOTIFY.NGT_GENERAL
                json_data['notification_type'] = NOTIFY.NT_GENERAL_COMMENTED
                json_data['post_id'] = post_comment.post_id
                json_data['post_comment_id'] = row_id

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True
                db.session.add(data)
                db.session.commit()
                # emit notification to user
                notify_user = User.query.get(data.user_id)
                # notification count for particular user
                # ncnt = notify_user.current_notification_count
                # User.query.filter(User.row_id == data.user_id). \
                #     update({User.current_notification_count: ncnt + 1})
                # notification count for particular user
                notify_user.current_notification_count += 1
                db.session.add(notify_user)
                db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_GENERAL,
                    'notification_type': NOTIFY.NT_GENERAL_COMMENTED},
                    namespace=SOCKETAPP.NS_NOTIFICATION,
                    room=notify_user.get_room_id(
                    room_type=SOCKETAPP.NS_NOTIFICATION))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_post_star_notifications(self, result, row_id, *args, **kwargs):
    """
    Adds a notification for post
    Notifies the post created user

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the event
    """

    if result:
        try:
            json_data = {}
            post_star = PostStar.query.filter(
                PostStar.row_id == row_id).options(joinedload(
                    PostStar.post).load_only(
                    'created_by', 'account_id')).first()
            if not post_star:
                return True
            if post_star.post.created_by != kwargs['log_uid']:
                json_data['user_id'] = post_star.post.created_by
                json_data['account_id'] = post_star.post.account_id
                json_data['post_id'] = post_star.post_id
                json_data['post_star_id'] = row_id
                json_data['notification_group'] = NOTIFY.NGT_GENERAL
                json_data['notification_type'] = NOTIFY.NT_GENERAL_STARRED

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True

                db.session.add(data)
                db.session.commit()
                # emit notification to user
                notify_user = User.query.get(data.user_id)
                # notification count for particular user
                # ncnt = notify_user.current_notification_count
                # User.query.filter(User.row_id == data.user_id). \
                #     update({User.current_notification_count: ncnt + 1})
                # notification count for particular user
                notify_user.current_notification_count += 1
                db.session.add(notify_user)
                db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_GENERAL,
                    'notification_type': NOTIFY.NT_GENERAL_STARRED},
                    namespace=SOCKETAPP.NS_NOTIFICATION,
                    room=notify_user.get_room_id(
                    room_type=SOCKETAPP.NS_NOTIFICATION))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_survey_notifications(self, result, row_id, invitee_ids,
                             *args, **kwargs):
    """
    Adds a notification for survey
    Notifies the survey invitee user
    """
    if result:
        try:
            json_data = {}
            survey_invite_data = SurveyResponse.query.filter(
                SurveyResponse.survey_id == row_id).options(load_only(
                    'row_id', 'survey_id')).first()
            if not survey_invite_data:
                return True

            if not invitee_ids:
                return True

            survey_participants_data = User.query.filter(
                User.row_id.in_(invitee_ids)).options(load_only(
                    'row_id', 'account_id')).all()
            if survey_participants_data:
                for survey_participant in survey_participants_data:
                    json_data['user_id'] = survey_participant.row_id
                    json_data['account_id'] = survey_participant.account_id
                    json_data['notification_group'] = NOTIFY.NGT_GENERAL
                    json_data['notification_type'] =\
                        NOTIFY.NT_GENERAL_SURVEY_INVITED
                    json_data['survey_id'] = \
                        survey_invite_data.survey_id

                    data, errors = NotificationSchema().load(json_data)
                    if errors:
                        return True
                    db.session.add(data)
                    db.session.commit()
                    # emit notification to user
                    notify_user = User.query.get(data.user_id)
                    # notification count for particular user
                    # ncnt = notify_user.current_notification_count
                    # User.query.filter(User.row_id == data.user_id). \
                    #     update({User.current_notification_count: ncnt + 1})
                    # notification count for particular user
                    notify_user.current_notification_count += 1
                    db.session.add(notify_user)
                    db.session.commit()
                    sockio.emit('new_notification', {
                        'user_id': data.user_id,
                        'notification_row_id': data.row_id,
                        'notification_group': NOTIFY.NGT_GENERAL,
                        'notification_type': NOTIFY.NT_GENERAL_SURVEY_INVITED},
                        namespace=SOCKETAPP.NS_NOTIFICATION,
                        room=notify_user.get_room_id(
                        room_type=SOCKETAPP.NS_NOTIFICATION))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_admin_publish_notifications(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for system user according account type select by admin
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            admin_publish_notify = AdminPublishNotification.query.get(row_id)

            if not admin_publish_notify:
                return True
            user_data = User.query.join(
                Account, Account.row_id == User.account_id).filter(and_(
                User.account_type.in_(
                    admin_publish_notify.account_type_preference),
                User.deleted.is_(False), User.unverified.is_(False),
                Account.domain_id == admin_publish_notify.domain_id)).all()
            for user in user_data:
                json_data['user_id'] = user.row_id
                json_data['account_id'] = user.account_id
                json_data['notification_group'] = NOTIFY.NGT_ADMIN
                json_data['notification_type'] = sub_type
                json_data['admin_publish_notification_id'] = row_id

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True
                db.session.add(data)
                db.session.commit()
                notify_user = User.query.get(data.user_id)
                # ncnt = user.current_notification_count
                # User.query.filter(User.row_id == data.user_id). \
                #     update({User.current_notification_count: ncnt + 1})
                # notification count for particular user
                notify_user.current_notification_count += 1
                db.session.add(notify_user)
                db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_ADMIN,
                    'notification_type': sub_type},
                            namespace=SOCKETAPP.NS_NOTIFICATION,
                            room=user.get_room_id(
                                room_type=SOCKETAPP.NS_NOTIFICATION))
                # send push notification for user
                if (user.settings.android_request_device_ids or
                        user.settings.ios_request_device_ids):
                    data = {
                        "content_available": True,
                        "priority": "high",
                        "show_in_foreground": True,
                        "data": {
                            "body": admin_publish_notify.description,
                            "title": admin_publish_notify.title,
                            "user_id": data.user_id,
                            "notification_row_id": data.row_id,
                            "redirect_row_id": data.row_id,
                            "notification_group": NOTIFY.NGT_ADMIN,
                            "notification_type": sub_type,
                            "sound": "default",
                            "click_action": "FCM_PLUGIN_ACTIVITY",
                            "icon": "icon"
                        }
                    }

                    if user.settings.android_request_device_ids:
                        data['registration_ids'] = user.settings. \
                            android_request_device_ids
                        android_response = push_notification(data)
                    if user.settings.ios_request_device_ids:
                        data['registration_ids'] = user.settings. \
                            ios_request_device_ids
                        data['notification'] = {
                            "body": data['data']['body'],
                            "title": data['data']['title']}
                        ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result
