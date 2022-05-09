"""
Notification related tasks, for each type of notification
"""

from flask import current_app
from sqlalchemy.orm import load_only
from sqlalchemy import and_, or_

from app import db, sockio
from app.common.utils import push_notification
from app.resources.notifications.schemas import NotificationSchema
from app.resources.users.models import User
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_hosts.models \
    import CorporateAccessEventHost
from app.corporate_access_resources.corporate_access_event_rsvps.models \
    import CorporateAccessEventRSVP
from \
    app.corporate_access_resources.corporate_access_event_participants.models \
    import CorporateAccessEventParticipant
from \
    app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.resources.notifications.models import Notification
from app.resources.notifications import constants as NOTIFY

from queueapp.tasks import celery_app, logger

from socketapp.base import constants as SOCKETAPP


@celery_app.task(bind=True, ignore_result=True)
def add_cae_invite_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate access event
    Notifies the corporate access event invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            event_invite_data = CorporateAccessEventInvitee.query.filter(
                CorporateAccessEventInvitee.corporate_access_event_id == row_id
            ).options(load_only('row_id', 'corporate_access_event_id',
                                'invitee_id', 'invitee_email')).all()
            if not event_invite_data:
                return True
            # send notification for all invitee one by one
            for event_invitee in event_invite_data:
                message_name['event_name'] = \
                    event_invitee.corporate_access_event.title
                message_name['first_name'] = \
                    event_invitee.corporate_access_event.creator.\
                    profile.first_name
                message_name['last_name'] = \
                    event_invitee.corporate_access_event.creator. \
                    profile.last_name
                event_invitee_data = None
                if event_invitee.invitee_id:
                    event_invitee_data = User.query.filter(
                        User.row_id == event_invitee.invitee_id).options(
                        load_only('row_id', 'account_id')).first()
                else:
                    # if external invitee as a system user
                    event_invitee_data = User.query.filter(
                        User.email == event_invitee.invitee_email
                    ).options(load_only('row_id', 'account_id')).first()

                if event_invitee_data:
                    json_data['user_id'] = event_invitee_data.row_id
                    json_data['account_id'] = event_invitee_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        event_invitee.corporate_access_event_id
                    # check if already notification generated for
                    # particular user
                    if Notification.query.filter(
                            and_(
                                Notification.user_id ==
                                event_invitee_data.row_id,
                                Notification.account_id ==
                                event_invitee_data.account_id,
                                Notification.notification_group ==
                                NOTIFY.NGT_COR_ACCESS_EVENT,
                                Notification.notification_type == sub_type,
                                Notification.corporate_access_event_id ==
                                event_invitee.corporate_access_event_id)
                            ).first():
                        continue

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                                "redirect_row_id": row_id,
                                "notification_group":
                                    NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_cae_host_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event
    Notifies the corporate_access_event host users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            event_host_data = CorporateAccessEventHost.query.filter(
                CorporateAccessEventHost.corporate_access_event_id == row_id
            ).options(load_only('row_id', 'corporate_access_event_id',
                                'host_id', 'host_email')).all()

            if not event_host_data:
                return True
            # send notification for all host one by one
            for event_host in event_host_data:
                message_name['event_name'] = \
                    event_host.corporate_access_event.title
                message_name['first_name'] = \
                    event_host.corporate_access_event.creator. \
                    profile.first_name
                message_name['last_name'] = \
                    event_host.corporate_access_event.creator. \
                    profile.last_name
                host_user_data = None
                if event_host.host_id:
                    host_user_data = User.query.filter(
                        User.row_id == event_host.host_id).options(
                        load_only('row_id', 'account_id')).first()
                else:
                    host_user_data = User.query.filter(
                        User.email == event_host.host_email).options(
                        load_only('row_id', 'account_id')).first()

                if host_user_data:
                    json_data['user_id'] = host_user_data.row_id
                    json_data['account_id'] = host_user_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        event_host.corporate_access_event_id
                    # check if already notification generated for
                    # particular user
                    if Notification.query.filter(
                            and_(
                                Notification.user_id ==
                                host_user_data.row_id,
                                Notification.account_id ==
                                host_user_data.account_id,
                                Notification.notification_group ==
                                NOTIFY.NGT_COR_ACCESS_EVENT,
                                Notification.notification_type == sub_type,
                                Notification.corporate_access_event_id ==
                                event_host.corporate_access_event_id)
                            ).first():
                        continue
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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                                "redirect_row_id": row_id,
                                "notification_group":
                                    NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_cae_rsvp_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event
    Notifies the corporate_access_event rsvp users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            event_rsvp_data = CorporateAccessEventRSVP.query.filter(
                CorporateAccessEventRSVP.corporate_access_event_id == row_id
            ).options(load_only(
                'row_id', 'corporate_access_event_id', 'email')).all()

            if not event_rsvp_data:
                return True
            # send notification for all rsvp one by one
            for rsvp_user_data in event_rsvp_data:
                message_name['event_name'] = \
                    rsvp_user_data.corporate_access_event.title
                rsvp_data = User.query.filter(
                    User.email == rsvp_user_data.email).options(load_only(
                        'row_id', 'account_id')).first()
                if rsvp_data:
                    json_data['user_id'] = rsvp_data.row_id
                    json_data['account_id'] = rsvp_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] = sub_type
                    json_data['corporate_access_event_id'] = \
                        rsvp_user_data.corporate_access_event_id
                    # check if already notification generated for
                    # particular user
                    if Notification.query.filter(
                            and_(
                                Notification.user_id ==
                                rsvp_data.row_id,
                                Notification.account_id ==
                                rsvp_data.account_id,
                                Notification.notification_group ==
                                NOTIFY.NGT_COR_ACCESS_EVENT,
                                Notification.notification_type == sub_type,
                                Notification.corporate_access_event_id ==
                                rsvp_data.corporate_access_event_id)
                            ).first():
                        continue
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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                                "redirect_row_id": row_id,
                                "notification_group":
                                    NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_cae_participant_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event
    Notifies the corporate_access_event participant users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            cor_participant_data = \
                CorporateAccessEventParticipant.query.filter(
                    CorporateAccessEventParticipant.
                    corporate_access_event_id ==
                    row_id).options(
                    load_only('row_id', 'corporate_access_event_id')).all()

            if not cor_participant_data:
                return True
            # send notification for all participant one by one
            for participant in cor_participant_data:
                message_name['event_name'] = \
                    participant.corporate_access_event.title
                message_name['first_name'] = \
                    participant.corporate_access_event.creator. \
                    profile.first_name
                message_name['last_name'] = \
                    participant.corporate_access_event.creator. \
                    profile.last_name
                if participant.participant_id:
                    corporate_participant_data = User.query.filter(
                        User.row_id == participant.participant_id
                    ).options(load_only('row_id', 'account_id')).first()
                else:
                    corporate_participant_data = User.query.filter(
                        User.email == participant.participant_email
                    ).options(load_only('row_id', 'account_id')).first()

                if corporate_participant_data:
                    json_data['user_id'] = corporate_participant_data.row_id
                    json_data['account_id'] = \
                        corporate_participant_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        participant.corporate_access_event_id
                    # check if already notification generated for
                    # particular user
                    if Notification.query.filter(
                            and_(
                                Notification.user_id ==
                                corporate_participant_data.row_id,
                                Notification.account_id ==
                                corporate_participant_data.account_id,
                                Notification.notification_group ==
                                NOTIFY.NGT_COR_ACCESS_EVENT,
                                Notification.notification_type == sub_type,
                                Notification.corporate_access_event_id ==
                                participant.corporate_access_event_id)
                            ).first():
                        continue
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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                                "redirect_row_id": row_id,
                                "notification_group":
                                    NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_cae_collaborator_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event
    Notifies the corporate_access_event collaborator users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            cor_collaborator_data = \
                CorporateAccessEventCollaborator.query.filter(
                    CorporateAccessEventCollaborator.
                    corporate_access_event_id ==
                    row_id).options(
                    load_only('row_id', 'corporate_access_event_id')).all()
            # send notification for all collaborator one by one
            for collaborator in cor_collaborator_data:
                message_name['event_name'] = \
                    collaborator.corporate_access_event.title
                if collaborator.collaborator_id:
                    corporate_collaborator_data = User.query.filter(
                        User.row_id == collaborator.collaborator_id
                    ).options(load_only('row_id', 'account_id')).first()
                else:
                    corporate_collaborator_data = User.query.filter(
                        User.email == collaborator.collaborator_email
                    ).options(load_only('row_id', 'account_id')).first()

                if corporate_collaborator_data:
                    json_data['user_id'] = corporate_collaborator_data.row_id
                    json_data['account_id'] = \
                        corporate_collaborator_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        collaborator.corporate_access_event_id
                    # check if already notification generated for
                    # particular user
                    if Notification.query.filter(
                            and_(
                                Notification.user_id ==
                                corporate_collaborator_data.row_id,
                                Notification.account_id ==
                                corporate_collaborator_data.account_id,
                                Notification.notification_group ==
                                NOTIFY.NGT_COR_ACCESS_EVENT,
                                Notification.notification_type == sub_type,
                                Notification.corporate_access_event_id ==
                                collaborator.corporate_access_event_id)
                            ).first():
                        continue

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                                "redirect_row_id": row_id,
                                "notification_group":
                                    NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_cae_updated_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate access event updated
    Notifies the corporate access event invitee users
    """
    if result:
        try:
            json_data = {}
            event_invitee_data = CorporateAccessEventInvitee.query.filter(
                CorporateAccessEventInvitee.corporate_access_event_id == row_id
            ).options(load_only(
                'row_id', 'corporate_access_event_id', 'invitee_id')).all()

            if not event_invitee_data:
                return True

            for invitee in event_invitee_data:
                invitee_data = User.query.filter(
                    User.row_id == invitee.invitee_id).options(load_only(
                        'row_id', 'account_id')).first()
                if invitee_data:
                    json_data['user_id'] = invitee_data.row_id
                    json_data['account_id'] = invitee_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        invitee.corporate_access_event_id

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
def add_cae_updated_participant_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event
    Notifies the corporate_access_event participant users
    """
    if result:
        try:
            json_data = {}
            cor_participant_data = \
                CorporateAccessEventParticipant.query.filter(
                    CorporateAccessEventParticipant.
                    corporate_access_event_id ==
                    row_id).options(
                    load_only('row_id', 'corporate_access_event_id')).all()

            if not cor_participant_data:
                return True

            for participant in cor_participant_data:
                if participant.participant_id:
                    corporate_participant_data = User.query.filter(
                        User.row_id == participant.participant_id
                    ).options(load_only('row_id', 'account_id')).first()
                else:
                    corporate_participant_data = User.query.filter(
                        User.email == participant.participant_email
                    ).options(load_only('row_id', 'account_id')).first()

                if corporate_participant_data:
                    json_data['user_id'] = corporate_participant_data.row_id
                    json_data['account_id'] = \
                        corporate_participant_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        participant.corporate_access_event_id

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
def add_cae_updated_collaborator_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event update
    Notifies the corporate_access_event collaborator users
    """
    if result:
        try:
            json_data = {}
            cor_collaborator_data = \
                CorporateAccessEventCollaborator.query.filter(
                    CorporateAccessEventCollaborator.
                    corporate_access_event_id ==
                    row_id).options(
                    load_only('row_id', 'corporate_access_event_id')).all()
            for collaborator in cor_collaborator_data:
                if collaborator.collaborator_id:
                    corporate_collaborator_data = User.query.filter(
                        User.row_id == collaborator.collaborator_id
                    ).options(load_only('row_id', 'account_id')).first()

                if corporate_collaborator_data:
                    json_data['user_id'] = corporate_collaborator_data.row_id
                    json_data['account_id'] = \
                        corporate_collaborator_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        collaborator.corporate_access_event_id

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
def add_cae_updated_host_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate access event updated
    Notifies the corporate access event host users
    """
    if result:
        try:
            json_data = {}
            event_host_data = CorporateAccessEventHost.query.filter(
                CorporateAccessEventHost.corporate_access_event_id == row_id
            ).options(load_only(
                'row_id', 'corporate_access_event_id', 'host_id')).all()

            if not event_host_data:
                return True

            for host in event_host_data:
                host_data = User.query.filter(
                    User.row_id == host.host_id).options(load_only(
                        'row_id', 'account_id')).first()
                if host_data:
                    json_data['user_id'] = host_data.row_id
                    json_data['account_id'] = host_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        host.corporate_access_event_id

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
def add_cae_updated_rsvp_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate_access_event
    Notifies the corporate_access_event rsvp users
    """
    if result:
        try:
            json_data = {}
            event_rsvp_data = CorporateAccessEventRSVP.query.filter(
                CorporateAccessEventRSVP.corporate_access_event_id == row_id
            ).options(load_only(
                'row_id', 'corporate_access_event_id', 'email')).all()

            if not event_rsvp_data:
                return True

            for rsvp_user_data in event_rsvp_data:
                rsvp_data = User.query.filter(
                    User.email == rsvp_user_data.email).options(load_only(
                        'row_id', 'account_id')).first()
                if rsvp_data:
                    json_data['user_id'] = rsvp_data.row_id
                    json_data['account_id'] = rsvp_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] = sub_type
                    json_data['corporate_access_event_id'] = \
                        rsvp_user_data.corporate_access_event_id

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
def add_cae_cancelled_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate access event cancelled
    Notifies the corporate access event invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            event_invitee_data = CorporateAccessEventInvitee.query.filter(
                CorporateAccessEventInvitee.corporate_access_event_id == row_id
            ).options(load_only(
                'corporate_access_event_id', 'invitee_id')).all()
            if not event_invitee_data:
                return True

            for event_invitee in event_invitee_data:
                message_name['event_name'] = \
                    event_invitee.corporate_access_event.title
                event_invitees_data = User.query.filter(or_(
                    User.email == event_invitee.invitee_email,
                    User.row_id == event_invitee.invitee_id)).options(
                    load_only('row_id', 'account_id')).first()
                if event_invitees_data:
                    json_data['user_id'] = event_invitees_data.row_id
                    json_data['account_id'] = event_invitees_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_COR_ACCESS_EVENT
                    json_data['notification_type'] =\
                        sub_type
                    json_data['corporate_access_event_id'] = \
                        event_invitee.corporate_access_event_id

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
                        'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                                "redirect_row_id":
                                    event_invitee.corporate_access_event_id,
                                "notification_group":
                                    NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_cae_invitee_joined_rejected_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for corporate access event creator when event joined or
    rejected by invitee user
    """

    if result:
        try:
            json_data = {}
            message_name = {}
            event_invitee_data = CorporateAccessEventInvitee.query.get(row_id)

            if not event_invitee_data:
                return True
            message_name['event_name'] = \
                event_invitee_data.corporate_access_event.title
            if event_invitee_data.invitee:
                message_name['first_name'] = event_invitee_data.invitee.profile.\
                    first_name
                message_name['last_name'] = event_invitee_data.invitee.profile.\
                    last_name
            else:
                message_name['first_name'] = event_invitee_data.\
                    invitee_first_name
                message_name['last_name'] = event_invitee_data.\
                    invitee_last_name
            event_creator_id = event_invitee_data.corporate_access_event.\
                created_by
            user = User.query.filter(
                User.row_id == event_creator_id).first()
            if user:
                json_data['user_id'] = user.row_id
                json_data['account_id'] = user.account_id
                json_data['notification_group'] = NOTIFY.NGT_COR_ACCESS_EVENT
                json_data['notification_type'] = sub_type
                json_data['corporate_access_event_invitee_id'] = row_id
                json_data['corporate_access_event_id'] =  \
                    event_invitee_data.corporate_access_event.row_id

                data, errors = NotificationSchema().load(json_data)
                if errors:
                    return True
                db.session.add(data)
                db.session.commit()
                notify_user = User.query.get(data.user_id)
                # notification count for particular user
                # ncnt = user.current_notification_count
                # User.query.filter(User.row_id == data.user_id). \
                #     update({User.current_notification_count: ncnt + 1})
                # notification count for particular user
                print(notify_user.current_notification_count,"before")
                ## already getting 1 count so commented below code
                # notify_user.current_notification_count += 1
                # db.session.add(notify_user)
                # db.session.commit()
                sockio.emit('new_notification', {
                    'user_id': data.user_id,
                    'notification_row_id': data.row_id,
                    'notification_group': NOTIFY.NGT_COR_ACCESS_EVENT,
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
                            "body": NOTIFY.NOTIFICATION_MESSAGES[
                                        sub_type] % message_name,
                            "title": current_app.config['BRAND_NAME'],
                            "user_id": data.user_id,
                            "notification_row_id": data.row_id,
                            "redirect_row_id": event_invitee_data.
                            corporate_access_event.row_id,
                            "notification_group":
                                NOTIFY.NGT_COR_ACCESS_EVENT,
                            "notification_type": sub_type,
                            "sound": "default",
                            "click_action": "FCM_PLUGIN_ACTIVITY",
                            "icon": "icon"
                        }
                    }
                    if user.settings.android_request_device_ids:
                        data['registration_ids'] = \
                            user.settings.android_request_device_ids
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
