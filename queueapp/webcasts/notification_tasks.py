"""
Notification related tasks, for each type of notification
"""

from flask import current_app
from sqlalchemy.orm import load_only

from app import db, sockio
from app.common.utils import push_notification
from app.resources.notifications.schemas import NotificationSchema
from app.resources.users.models import User
from app.resources.notifications import constants as NOTIFY

from app.webcast_resources.webcast_invitees.models import WebcastInvitee
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_participants.models import \
    WebcastParticipant
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP


from queueapp.tasks import celery_app, logger

from socketapp.base import constants as SOCKETAPP


@celery_app.task(bind=True, ignore_result=True)
def add_webcast_invite_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast
    Notifies the webcast invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            webcast_invite_data = WebcastInvitee.query.filter(
                WebcastInvitee.webcast_id == row_id
            ).options(load_only('row_id', 'webcast_id', 'invitee_id',
                                'invitee_email')).all()
            if not webcast_invite_data:
                return True

            if webcast_invite_data:
                for webcast_invitee in webcast_invite_data:
                    webcast_invitee_data = None
                    message_name['event_name'] = webcast_invitee.webcast.title
                    message_name['first_name'] = \
                        webcast_invitee.webcast.creator.profile.first_name
                    message_name['last_name'] = \
                        webcast_invitee.webcast.creator.profile.last_name
                    if webcast_invitee.invitee_id:
                        webcast_invitee_data = User.query.filter(
                            User.row_id == webcast_invitee.invitee_id).options(
                            load_only('row_id', 'account_id')).first()
                    else:
                        webcast_invitee_data = User.query.filter(
                            User.email == webcast_invitee.invitee_email).\
                            options(load_only('row_id', 'account_id')).first()

                    if webcast_invitee_data:
                        json_data['user_id'] = webcast_invitee_data.row_id
                        json_data['account_id'] = \
                            webcast_invitee_data.account_id
                        json_data['notification_group'] = \
                            NOTIFY.NGT_WEBCAST
                        json_data['notification_type'] =\
                            sub_type
                        json_data['webcast_id'] = \
                            webcast_invitee.webcast_id
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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
                                "notification_group": NOTIFY.NGT_WEBCAST,
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
def add_webcast_host_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast
    Notifies the webcast host users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_host_data = WebcastHost.query.filter(
                WebcastHost.webcast_id == row_id
            ).options(load_only('row_id', 'webcast_id', 'host_id',
                                'host_email')).all()

            if not web_host_data:
                return True

            if web_host_data:
                for webcast_host in web_host_data:
                    webcast_host_data = None
                    message_name['event_name'] = webcast_host.webcast.title
                    message_name['first_name'] = \
                        webcast_host.webcast.creator.profile.first_name
                    message_name['last_name'] = \
                        webcast_host.webcast.creator.profile.last_name
                    if webcast_host.host_id:
                        webcast_host_data = User.query.filter(
                            User.row_id == webcast_host.host_id).options(
                            load_only('row_id', 'account_id')).first()
                    else:
                        webcast_host_data = User.query.filter(
                            User.email == webcast_host.host_email).options(
                            load_only('row_id', 'account_id')).first()

                    if webcast_host_data:
                        json_data['user_id'] = webcast_host_data.row_id
                        json_data['account_id'] = webcast_host_data.account_id
                        json_data['notification_group'] = \
                            NOTIFY.NGT_WEBCAST
                        json_data['notification_type'] =\
                            sub_type
                        json_data['webcast_id'] = \
                            webcast_host.webcast_id

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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
                                "notification_group": NOTIFY.NGT_WEBCAST,
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
def add_webcast_participant_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast
    Notifies the webcast participant users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_participant_data = WebcastParticipant.query.filter(
                WebcastParticipant.webcast_id == row_id).options(
                load_only('row_id', 'webcast_id', 'participant_id',
                          'participant_email')).all()

            if not web_participant_data:
                return True

            if web_participant_data:
                webcast_pcpt_user = None
                for webcast_participant in web_participant_data:
                    message_name['event_name'] = webcast_participant.\
                        webcast.title
                    message_name['first_name'] = \
                        webcast_participant.webcast.creator.profile.first_name
                    message_name['last_name'] = \
                        webcast_participant.webcast.creator.profile.last_name
                    if webcast_participant.participant_id:
                        webcast_pcpt_user = User.query.filter(
                            User.row_id == webcast_participant.participant_id
                        ).options(load_only('row_id', 'account_id')).first()
                    else:
                        webcast_pcpt_user = User.query.filter(
                            User.email == webcast_participant.participant_email
                        ).options(load_only('row_id', 'account_id')).first()

                    if webcast_pcpt_user:
                        json_data['user_id'] = webcast_pcpt_user.row_id
                        json_data['account_id'] = webcast_pcpt_user.account_id
                        json_data['notification_group'] = \
                            NOTIFY.NGT_WEBCAST
                        json_data['notification_type'] =\
                            sub_type
                        json_data['webcast_id'] = \
                            webcast_participant.webcast_id

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
                            'notification_group': NOTIFY.NGT_WEBCAST,
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
                                    "notification_group": NOTIFY.NGT_WEBCAST,
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
                                data['registration_ids'] = \
                                    notify_user.settings.ios_request_device_ids
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
def add_webcast_rsvp_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast
    Notifies the webcast rsvp users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_rsvp_data = WebcastRSVP.query.filter(
                WebcastRSVP.webcast_id == row_id
            ).options(load_only('row_id', 'webcast_id', 'email')).all()

            if not web_rsvp_data:
                return True

            for webcast_rsvp_data in web_rsvp_data:
                message_name['event_name'] = web_rsvp_data.webcast.title
                rsvp_data = User.query.filter(
                    User.email == webcast_rsvp_data.email).options(load_only(
                        'row_id', 'account_id')).first()
                if rsvp_data:
                    json_data['user_id'] = rsvp_data.row_id
                    json_data['account_id'] = rsvp_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBCAST
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        webcast_rsvp_data.webcast_id

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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
                                "notification_group": NOTIFY.NGT_WEBCAST,
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
def add_webcast_updated_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast updated
    Notifies the webcast invitee users
    """
    if result:
        try:
            json_data = {}
            webcast_invitee_data = WebcastInvitee.query.filter(
                WebcastInvitee.webcast_id == row_id).options(load_only(
                    'row_id', 'webcast_id', 'invitee_id')).all()

            if not webcast_invitee_data:
                return True

            for invitee in webcast_invitee_data:
                invitee_data = User.query.filter(
                    User.row_id == invitee.invitee_id).options(load_only(
                        'row_id', 'account_id')).first()
                if invitee_data:
                    json_data['user_id'] = invitee_data.row_id
                    json_data['account_id'] = invitee_data.account_id
                    json_data['notification_group'] = NOTIFY.NGT_WEBCAST
                    json_data['notification_type'] = sub_type
                    json_data['webcast_id'] = invitee.webcast_id

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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
def add_webcast_updated_participant_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast
    Notifies the webcast participant users
    """
    if result:
        try:
            json_data = {}
            web_participant_data = WebcastParticipant.query.filter(
                WebcastParticipant.webcast_id == row_id).options(
                load_only('row_id', 'webcast_id')).all()

            if not web_participant_data:
                return True

            for participant in web_participant_data:
                if participant.participant_id:
                    webcast_participant_data = User.query.filter(
                        User.row_id == participant.participant_id
                    ).options(load_only('row_id', 'account_id')).first()
                else:
                    webcast_participant_data = User.query.filter(
                        User.email == participant.participant_email
                    ).options(load_only('row_id', 'account_id')).first()

                if webcast_participant_data:
                    json_data['user_id'] = webcast_participant_data.row_id
                    json_data['account_id'] = \
                        webcast_participant_data.account_id
                    json_data['notification_group'] = NOTIFY.NGT_WEBCAST
                    json_data['notification_type'] = sub_type
                    json_data['webcast_id'] = participant.webcast_id

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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
def add_webcast_updated_host_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast updated
    Notifies the webcast host users
    """
    if result:
        try:
            json_data = {}
            webcast_host_data = WebcastHost.query.filter(
                WebcastHost.webcast_id == row_id).options(load_only(
                    'row_id', 'webcast_id', 'host_id')).all()

            if not webcast_host_data:
                return True

            for host in webcast_host_data:
                host_data = User.query.filter(
                    User.row_id == host.host_id).options(load_only(
                        'row_id', 'account_id')).first()
                if host_data:
                    json_data['user_id'] = host_data.row_id
                    json_data['account_id'] = host_data.account_id
                    json_data['notification_group'] = NOTIFY.NGT_WEBCAST
                    json_data['notification_type'] = sub_type
                    json_data['webcast_id'] = host.webcast_id

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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
def add_webcast_updated_rsvp_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast
    Notifies the webcast rsvp users
    """
    if result:
        try:
            json_data = {}
            webcast_rsvp_data = WebcastRSVP.query.filter(
                WebcastRSVP.webcast_id == row_id).options(load_only(
                    'row_id', 'webcast_id', 'email')).all()

            if not webcast_rsvp_data:
                return True

            for rsvp_user_data in webcast_rsvp_data:
                rsvp_data = User.query.filter(
                    User.email == rsvp_user_data.email).options(load_only(
                        'row_id', 'account_id')).first()
                if rsvp_data:
                    json_data['user_id'] = rsvp_data.row_id
                    json_data['account_id'] = rsvp_data.account_id
                    json_data['notification_group'] = NOTIFY.NGT_WEBCAST
                    json_data['notification_type'] = sub_type
                    json_data['webcast_id'] = rsvp_user_data.webcast_id

                    data, errors = NotificationSchema().load(json_data)
                    if errors:
                        return True
                    db.session.add(data)
                    db.session.commit()
                    # emit notification to user
                    notify_user = User.query.get(data.user_id)
                    # notification count for particular user
                    notify_user.current_notification_count += 1
                    db.session.add(notify_user)
                    db.session.commit()
                    sockio.emit('new_notification', {
                        'user_id': data.user_id,
                        'notification_row_id': data.row_id,
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
def add_webcast_cancelled_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webcast cancelled
    Notifies the webcast invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            webcast_invitee_data = WebcastInvitee.query.filter(
                WebcastInvitee.webcast_id == row_id).options(load_only(
                    'webcast_id', 'invitee_id')).all()
            if not webcast_invitee_data:
                return True

            for webcast_invitee in webcast_invitee_data:
                message_name['event_name'] = webcast_invitee.webcast.title
                webcast_invitees_data = User.query.filter(
                    User.row_id == webcast_invitee.invitee_id).options(
                    load_only('row_id', 'account_id')).first()
                if webcast_invitees_data:
                    json_data['user_id'] = webcast_invitees_data.row_id
                    json_data['account_id'] = webcast_invitees_data.account_id
                    json_data['notification_group'] = NOTIFY.NGT_WEBCAST
                    json_data['notification_type'] = sub_type
                    json_data['webcast_id'] = webcast_invitee.webcast_id

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
                        'notification_group': NOTIFY.NGT_WEBCAST,
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
                                "notification_group": NOTIFY.NGT_WEBCAST,
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
