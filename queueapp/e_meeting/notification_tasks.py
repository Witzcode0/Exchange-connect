"""
Notification related tasks, for each type of notification
"""

from flask import current_app
from sqlalchemy.orm import load_only
from sqlalchemy import and_

from app import db, sockio
from app.common.utils import push_notification
from app.resources.notifications.schemas import NotificationSchema
from app.resources.users.models import User
from app.resources.notifications import constants as NOTIFY
from app.resources.accounts import constants as ACCOUNT

from app.toolkit_resources.project_e_meeting_invitee.models import (
    EmeetingInvitee)

from queueapp.tasks import celery_app, logger

from socketapp.base import constants as SOCKETAPP


@celery_app.task(bind=True, ignore_result=True)
def add_emeeting_invite_notification(
        self, result, emeeting_invitees, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for e_meeting
    Notifies the e_meeting invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            meeting_invite_data = EmeetingInvitee.query.filter(and_(
                EmeetingInvitee.invitee_id.in_(emeeting_invitees),
                EmeetingInvitee.e_meeting_id == row_id)).all()
            if not meeting_invite_data:
                return True

            # if meeting_invite_data:
            for e_meeting_invitee in meeting_invite_data:
                message_name['event_name'] = e_meeting_invitee.e_meeting.meeting_subject
                message_name['first_name'] = \
                    e_meeting_invitee.e_meeting.creator.profile.first_name
                message_name['last_name'] = \
                    e_meeting_invitee.e_meeting.creator.profile.last_name
                e_meeting_invitee_data = None
                if e_meeting_invitee.invitee_id:
                    e_meeting_invitee_data = User.query.filter(
                        User.row_id == e_meeting_invitee.invitee_id).options(load_only('row_id', 'account_id')).first()

                if e_meeting_invitee_data:
                    json_data['user_id'] = e_meeting_invitee_data.row_id
                    json_data['account_id'] = \
                        e_meeting_invitee_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_EMEETING
                    json_data['notification_type'] =\
                        sub_type
                    json_data['e_meeting_id'] = \
                        e_meeting_invitee.e_meeting_id
                    json_data['project_id'] = e_meeting_invitee.e_meeting.project_id
                    # #TODO: check notification if already exists for
                    # particular user
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
                    if notify_user.account_type == ACCOUNT.ACCT_ADMIN:
                        namespace = SOCKETAPP.NS_NOTIFICATION
                    else:
                        namespace = SOCKETAPP.NS_DESIGNLAB_NOTIFICATION
                    sockio.emit('new_notification', {
                        'user_id': data.user_id,
                        'notification_row_id': data.row_id,
                        'notification_group': NOTIFY.NGT_EMEETING,
                        'notification_type': sub_type},
                        namespace=namespace,
                        room=notify_user.get_room_id(
                        room_type=namespace))
                    # send push notification for user
                    '''if (notify_user.settings.android_request_device_ids or
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
                                "redirect_row_id": row_id,
                                "notification_group": NOTIFY.NGT_EMEETING,
                                "notification_type": sub_type,
                                "sound": "default",
                                "click_action": "FCM_PLUGIN_ACTIVITY",
                                "icon": "icon"
                            }
                        }
                        if notify_user.settings.android_request_device_ids:
                            data['registration_ids'] = \
                                notify_user.settings.\
                                android_request_device_ids
                            android_response = push_notification(data)
                        if notify_user.settings.ios_request_device_ids:
                            data['registration_ids'] = notify_user.settings. \
                                ios_request_device_ids
                            data['notification'] = {
                                "body": data['data']['body'],
                                "title": data['data']['title']}
                            ios_response = push_notification(data)'''
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_emeeting_updated_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for e_meeting update
    Notifies the e_meeting invitee users
    """
    if result:
        try:
            json_data = {}
            meeting_invite_data = \
                EmeetingInvitee.query.filter(
                    EmeetingInvitee.e_meeting_id == row_id).options(
                    load_only('row_id', 'e_meeting_id')).all()
            for invitee in meeting_invite_data:
                if invitee.invitee_id:
                    e_meeting_invitee_data = User.query.filter(
                        User.row_id == invitee.invitee_id
                    ).options(load_only('row_id', 'account_id')).first()

                    if e_meeting_invitee_data:
                        json_data['user_id'] = e_meeting_invitee_data.row_id
                        json_data['account_id'] = \
                            e_meeting_invitee_data.account_id
                        json_data['notification_group'] = \
                            NOTIFY.NGT_EMEETING
                        json_data['notification_type'] =\
                            sub_type
                        json_data['e_meeting_id'] = \
                            invitee.e_meeting_id
                        json_data['project_id'] = invitee.e_meeting.project_id

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
                        if notify_user.account_type == ACCOUNT.ACCT_ADMIN:
                            namespace = SOCKETAPP.NS_NOTIFICATION
                        else:
                            namespace = SOCKETAPP.NS_DESIGNLAB_NOTIFICATION
                        sockio.emit('new_notification', {
                            'user_id': data.user_id,
                            'notification_row_id': data.row_id,
                            'notification_group': NOTIFY.NGT_EMEETING,
                            'notification_type': sub_type},
                            namespace=namespace,
                            room=notify_user.get_room_id(
                            room_type=namespace))

            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_emeeting_cancelled_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for e_meeting cancelled
    Notifies the e_meeting invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            meeting_invitee_data = EmeetingInvitee.query.filter(
                EmeetingInvitee.e_meeting_id == row_id
            ).options(load_only(
                'e_meeting_id', 'invitee_id')).all()
            if not meeting_invitee_data:
                return True

            for invitee in meeting_invitee_data:
                message_name['event_name'] = invitee.e_meeting.meeting_subject
                meeting_invitee = User.query.filter(
                    User.row_id == invitee.invitee_id).options(
                    load_only('row_id', 'account_id')).first()
                if meeting_invitee:
                    json_data['user_id'] = meeting_invitee.row_id
                    json_data['account_id'] = meeting_invitee.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_EMEETING
                    json_data['notification_type'] =\
                        sub_type
                    json_data['e_meeting_id'] = \
                        invitee.e_meeting_id
                    json_data['project_id'] = invitee.e_meeting.project_id

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
                    if notify_user.account_type == ACCOUNT.ACCT_ADMIN:
                        namespace = SOCKETAPP.NS_NOTIFICATION
                    else:
                        namespace = SOCKETAPP.NS_DESIGNLAB_NOTIFICATION
                    sockio.emit('new_notification', {
                        'user_id': data.user_id,
                        'notification_row_id': data.row_id,
                        'notification_group': NOTIFY.NGT_EMEETING,
                        'notification_type': sub_type},
                        namespace=namespace,
                        room=notify_user.get_room_id(
                        room_type=namespace))
                    # send push notification for user
                    '''if (notify_user.settings.android_request_device_ids or
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
                                "redirect_row_id": row_id,
                                "notification_group": NOTIFY.NGT_EMEETING,
                                "notification_type": sub_type,
                                "sound": "default",
                                "click_action": "FCM_PLUGIN_ACTIVITY",
                                "icon": "icon"
                            }
                        }
                        if notify_user.settings.android_request_device_ids:
                            data['registration_ids'] = \
                                notify_user.settings.android_request_device_ids
                            android_response = push_notification(data)
                        if notify_user.settings.ios_request_device_ids:
                            data['registration_ids'] = notify_user.settings. \
                                ios_request_device_ids
                            data['notification'] = {
                                "body": data['data']['body'],
                                "title": data['data']['title']}
                            ios_response = push_notification(data)'''
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result