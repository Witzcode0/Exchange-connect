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

from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_hosts.models import WebinarHost
from app.webinar_resources.webinar_participants.models import \
    WebinarParticipant
from app.webinar_resources.webinar_rsvps.models import WebinarRSVP


from queueapp.tasks import celery_app, logger

from socketapp.base import constants as SOCKETAPP


@celery_app.task(bind=True, ignore_result=True)
def add_webinar_invite_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar
    Notifies the webinar invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_invite_data = WebinarInvitee.query.filter(
                WebinarInvitee.webinar_id == row_id
            ).options(load_only('row_id', 'webinar_id', 'invitee_id',
                                'invitee_email')).all()
            if not web_invite_data:
                return True

            if web_invite_data:
                for webinar_invitee in web_invite_data:
                    message_name['event_name'] = webinar_invitee.webinar.title
                    message_name['first_name'] = \
                        webinar_invitee.webinar.creator.profile.first_name
                    message_name['last_name'] = \
                        webinar_invitee.webinar.creator.profile.last_name
                    webinar_invitee_data = None
                    if webinar_invitee.invitee_id:
                        webinar_invitee_data = User.query.filter(
                            User.row_id == webinar_invitee.invitee_id).options(
                            load_only('row_id', 'account_id')).first()
                    else:
                        webinar_invitee_data = User.query.filter(
                            User.email == webinar_invitee.invitee_email).\
                            options(load_only('row_id', 'account_id')).first()

                    if webinar_invitee_data:
                        json_data['user_id'] = webinar_invitee_data.row_id
                        json_data['account_id'] = \
                            webinar_invitee_data.account_id
                        json_data['notification_group'] = \
                            NOTIFY.NGT_WEBINAR
                        json_data['notification_type'] =\
                            sub_type
                        json_data['webinar_id'] = \
                            webinar_invitee.webinar_id
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
                        sockio.emit('new_notification', {
                            'user_id': data.user_id,
                            'notification_row_id': data.row_id,
                            'notification_group': NOTIFY.NGT_WEBINAR,
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
                                    "notification_group": NOTIFY.NGT_WEBINAR,
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
                                ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_webinar_host_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar
    Notifies the webinar host users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_host_data = WebinarHost.query.filter(
                WebinarHost.webinar_id == row_id
            ).options(load_only('row_id', 'webinar_id', 'host_id',
                                'host_email')).all()
            if not web_host_data:
                return True

            if web_host_data:
                for webinar_host in web_host_data:
                    message_name['event_name'] = webinar_host.webinar.title
                    message_name['first_name'] = \
                        webinar_host.webinar.creator.profile.first_name
                    message_name['last_name'] = \
                        webinar_host.webinar.creator.profile.last_name
                    webinar_host_data = None
                    if webinar_host.host_id:
                        webinar_host_data = User.query.filter(
                            User.row_id == webinar_host.host_id).options(
                            load_only('row_id', 'account_id')).first()
                    else:
                        webinar_host_data = User.query.filter(
                            User.email == webinar_host.host_email).options(
                            load_only('row_id', 'account_id')).first()

                    if webinar_host_data:
                        json_data['user_id'] = webinar_host_data.row_id
                        json_data['account_id'] = webinar_host_data.account_id
                        json_data['notification_group'] = \
                            NOTIFY.NGT_WEBINAR
                        json_data['notification_type'] =\
                            sub_type
                        json_data['webinar_id'] = \
                            webinar_host.webinar_id
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
                        sockio.emit('new_notification', {
                            'user_id': data.user_id,
                            'notification_row_id': data.row_id,
                            'notification_group': NOTIFY.NGT_WEBINAR,
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
                                    "notification_group": NOTIFY.NGT_WEBINAR,
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
                                ios_response = push_notification(data)
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def add_webinar_participant_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar
    Notifies the webinar participant users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_participant_data = WebinarParticipant.query.filter(
                WebinarParticipant.webinar_id == row_id
            ).options(load_only('row_id', 'webinar_id')).all()

            if not web_participant_data:
                return True

            for participant in web_participant_data:
                message_name['event_name'] = participant.webinar.title
                message_name['first_name'] = \
                    participant.webinar.creator.profile.first_name
                message_name['last_name'] = \
                    participant.webinar.creator.profile.last_name
                if participant.participant_id:
                    webinar_participant_data = User.query.filter(
                        User.row_id == participant.participant_id
                    ).options(load_only('row_id', 'account_id')).first()
                else:
                    webinar_participant_data = User.query.filter(
                        User.email == participant.participant_email
                    ).options(load_only('row_id', 'account_id')).first()

                if webinar_participant_data:
                    json_data['user_id'] = webinar_participant_data.row_id
                    json_data['account_id'] = \
                        webinar_participant_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        participant.webinar_id
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
                    sockio.emit('new_notification', {
                        'user_id': data.user_id,
                        'notification_row_id': data.row_id,
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
                                "notification_group": NOTIFY.NGT_WEBINAR,
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
def add_webinar_rsvp_added_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar
    Notifies the webinar rsvp users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_rsvp_data = WebinarRSVP.query.filter(
                WebinarRSVP.webinar_id == row_id
            ).options(load_only('row_id', 'webinar_id', 'email')).all()

            if not web_rsvp_data:
                return True

            for webinar_rsvp_data in web_rsvp_data:
                message_name['event_name'] = webinar_rsvp_data.webinar.title
                rsvp_data = User.query.filter(
                    User.email == webinar_rsvp_data.email).options(load_only(
                        'row_id', 'account_id')).first()
                if rsvp_data:
                    json_data['user_id'] = rsvp_data.row_id
                    json_data['account_id'] = rsvp_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        webinar_rsvp_data.webinar_id

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
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
                                "notification_group": NOTIFY.NGT_WEBINAR,
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
def add_webinar_updated_participant_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar
    Notifies the webinar participant users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_participant_data = \
                WebinarParticipant.query.filter(
                    WebinarParticipant.webinar_id == row_id).\
                options(load_only('row_id', 'webinar_id')).all()

            if not web_participant_data:
                return True

            for participant in web_participant_data:
                if participant.participant_id:
                    webinar_participant_data = User.query.filter(
                        User.row_id == participant.participant_id
                    ).options(load_only('row_id', 'account_id')).first()
                else:
                    webinar_participant_data = User.query.filter(
                        User.email == participant.participant_email
                    ).options(load_only('row_id', 'account_id')).first()

                if webinar_participant_data:
                    json_data['user_id'] = webinar_participant_data.row_id
                    json_data['account_id'] = \
                        webinar_participant_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        participant.webinar_id

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
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
def add_webinar_updated_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar update
    Notifies the webinar invitee users
    """
    if result:
        try:
            json_data = {}
            web_invitee_data = \
                WebinarInvitee.query.filter(
                    WebinarInvitee.webinar_id == row_id).options(
                    load_only('row_id', 'webinar_id')).all()
            for invitee in web_invitee_data:
                if invitee.invitee_id:
                    webinar_invitee_data = User.query.filter(
                        User.row_id == invitee.invitee_id
                    ).options(load_only('row_id', 'account_id')).first()

                if webinar_invitee_data:
                    json_data['user_id'] = webinar_invitee_data.row_id
                    json_data['account_id'] = \
                        webinar_invitee_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        invitee.webinar_id

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
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
def add_webinar_updated_host_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar updated
    Notifies the webinar host users
    """
    if result:
        try:
            json_data = {}
            web_host_data = WebinarHost.query.filter(
                WebinarHost.webinar_id == row_id
            ).options(load_only(
                'row_id', 'webinar_id', 'host_id')).all()

            if not web_host_data:
                return True

            for host in web_host_data:
                host_data = User.query.filter(
                    User.row_id == host.host_id).options(load_only(
                        'row_id', 'account_id')).first()
                if host_data:
                    json_data['user_id'] = host_data.row_id
                    json_data['account_id'] = host_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        host.webinar_id

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
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
def add_webinar_updated_rsvp_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar
    Notifies the webinar rsvp users
    """
    if result:
        try:
            json_data = {}
            web_rsvp_data = WebinarRSVP.query.filter(
                WebinarRSVP.webinar_id == row_id
            ).options(load_only(
                'row_id', 'webinar_id', 'email')).all()

            if not web_rsvp_data:
                return True

            for rsvp_user_data in web_rsvp_data:
                rsvp_data = User.query.filter(
                    User.email == rsvp_user_data.email).options(load_only(
                        'row_id', 'account_id')).first()
                if rsvp_data:
                    json_data['user_id'] = rsvp_data.row_id
                    json_data['account_id'] = rsvp_data.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] = sub_type
                    json_data['webinar_id'] = \
                        rsvp_user_data.webinar_id

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
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
def add_webinar_cancelled_invitee_notification(
        self, result, row_id, sub_type, *args, **kwargs):
    """
    Adds a notification for webinar cancelled
    Notifies the webinar invitee users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            web_invitee_data = WebinarInvitee.query.filter(
                WebinarInvitee.webinar_id == row_id
            ).options(load_only(
                'webinar_id', 'invitee_id')).all()
            if not web_invitee_data:
                return True

            for invitee in web_invitee_data:
                message_name['event_name'] = invitee.webinar.title
                web_invitee = User.query.filter(
                    User.row_id == invitee.invitee_id).options(
                    load_only('row_id', 'account_id')).first()
                if web_invitee:
                    json_data['user_id'] = web_invitee.row_id
                    json_data['account_id'] = web_invitee.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_WEBINAR
                    json_data['notification_type'] =\
                        sub_type
                    json_data['webinar_id'] = \
                        invitee.webinar_id

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
                        'notification_group': NOTIFY.NGT_WEBINAR,
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
                                "notification_group": NOTIFY.NGT_WEBINAR,
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
