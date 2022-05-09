"""
Notification related tasks, for each type of notification
"""

from flask import current_app
from sqlalchemy import and_

from app import db, sockio
from app.common.utils import push_notification
from app.resources.notifications.schemas import NotificationSchema
from app.resources.users.models import User
from app.corporate_access_resources.ca_open_meetings.models import \
    CAOpenMeeting
from app.corporate_access_resources.ca_open_meeting_inquiries.models import \
    CAOpenMeetingInquiry
from app.resources.notifications.models import Notification
from app.resources.notifications import constants as NOTIFY
from app.corporate_access_resources.corporate_access_event_inquiries \
    import constants as INQUIRIES

from queueapp.tasks import celery_app, logger

from socketapp.base import constants as SOCKETAPP


@celery_app.task(bind=True, ignore_result=True)
def add_caom_slot_inquiry_generated_notification(
        self, result, inquiry_id, sub_type, *args, **kwargs):
    """
    Adds a notification for ca open meeting
    Notifies the ca open meeting creator when invitee inquiries any slot
    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param inquiry_id:
        the row_id of the ca_open_meeting_inquiry
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            caom_inquiry = CAOpenMeetingInquiry.query.get(inquiry_id)
            if not caom_inquiry:
                return True
            message_name['first_name'] = caom_inquiry.creator.profile.\
                first_name
            message_name['last_name'] = caom_inquiry.creator.profile. \
                last_name
            json_data['user_id'] = caom_inquiry.ca_open_meeting.creator.row_id
            json_data['account_id'] = \
                caom_inquiry.ca_open_meeting.creator.account_id
            json_data['notification_group'] = NOTIFY.NGT_CA_OPEN_MEETING
            json_data['notification_type'] = sub_type
            json_data['ca_open_meeting_id'] = \
                caom_inquiry.ca_open_meeting_id
            json_data['ca_open_meeting_inquiry_id'] = caom_inquiry.row_id
            json_data['ca_open_meeting_slot_id'] = \
                caom_inquiry.ca_open_meeting_slot_id
            json_data['caom_slot_name'] = \
                caom_inquiry.ca_open_meeting_slot.slot_name
            message_name['event_name'] = caom_inquiry.ca_open_meeting.title
            message_name['slot_name'] = \
                caom_inquiry.ca_open_meeting_slot.slot_name

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
                'notification_group': NOTIFY.NGT_CA_OPEN_MEETING,
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
                        "redirect_row_id": caom_inquiry.ca_open_meeting_id,
                        "notification_group": NOTIFY.NGT_CA_OPEN_MEETING,
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
def add_caom_slot_inquiry_confirmed_notification(
        self, result, inquiry_id, sub_type, *args, **kwargs):
    """
    Adds a notification for ca open meeting
    Notifies the ca open meeting invitee inquirer when meeting creator confirms
    his inquiry.
    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param inquiry_id:
        the row_id of the ca_open_meeting_inquiry
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            caom_inquiry = CAOpenMeetingInquiry.query.get(inquiry_id)
            if not caom_inquiry:
                return True
            json_data['user_id'] = caom_inquiry.creator.row_id
            json_data['account_id'] = caom_inquiry.creator.account_id
            json_data['notification_group'] = NOTIFY.NGT_CA_OPEN_MEETING
            json_data['notification_type'] = sub_type
            json_data['ca_open_meeting_id'] = \
                caom_inquiry.ca_open_meeting_id
            json_data['ca_open_meeting_inquiry_id'] = caom_inquiry.row_id
            json_data['ca_open_meeting_slot_id'] = \
                caom_inquiry.ca_open_meeting_slot_id
            json_data['caom_slot_name'] = \
                caom_inquiry.ca_open_meeting_slot.slot_name
            message_name['slot_name'] = \
                caom_inquiry.ca_open_meeting_slot.slot_name
            message_name['event_name'] = caom_inquiry.ca_open_meeting.title

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
                'notification_group': NOTIFY.NGT_CA_OPEN_MEETING,
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
                        "redirect_row_id": caom_inquiry.ca_open_meeting_id,
                        "notification_group": NOTIFY.NGT_CA_OPEN_MEETING,
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
def add_caom_slot_deleted_notification(
        self, result, caom_id, caom_slot_name,
        slot_inquirer_user_ids, sub_type, *args, **kwargs):
    """
    Adds a notification for ca open meeting
    Notifies the ca open meeting invitee confirmed inquirer when particular
    slot deletes.
    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param caom_id:
        the row id of the ca_open_meeting
    :param caom_slot_name:
        the name of ca_open_meeting_slot
    :param slot_inquirer_user_ids:
       the created_by value of inquirers i.e. invitee_ids
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            caom = CAOpenMeeting.query.get(caom_id)

            if not caom and not slot_inquirer_user_ids:
                return True

            for slot_inquirer_user_id in slot_inquirer_user_ids:
                slot_inquirer_user = User.query.filter_by(
                    row_id=slot_inquirer_user_id).first()
                if slot_inquirer_user:
                    json_data['user_id'] = slot_inquirer_user.row_id
                    json_data['account_id'] = slot_inquirer_user.account_id
                    json_data['notification_group'] = \
                        NOTIFY.NGT_CA_OPEN_MEETING
                    json_data['notification_type'] = sub_type
                    json_data['ca_open_meeting_id'] = caom_id
                    json_data['caom_slot_name'] = caom_slot_name
                    message_name['slot_name'] = caom_slot_name
                    message_name['event_name'] = caom.title
                    # check if already notification generated for
                    # particular user
                    if Notification.query.filter(and_(
                            Notification.user_id == slot_inquirer_user.row_id,
                            Notification.account_id ==
                            slot_inquirer_user.account_id,
                            Notification.notification_group ==
                            NOTIFY.NGT_CA_OPEN_MEETING,
                            Notification.notification_type == sub_type,
                            Notification.ca_open_meeting_id == caom_id,
                            Notification.caom_slot_name ==
                            caom_slot_name)).first():
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
                        'notification_group': NOTIFY.NGT_CA_OPEN_MEETING,
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
                                "redirect_row_id": caom.row_id,
                                "notification_group":
                                    NOTIFY.NGT_CA_OPEN_MEETING,
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
def add_caom_cancelled_notification(
        self, result, caom_id, sub_type, *args, **kwargs):
    """
    Adds a notification for ca open meeting
    Notifies the ca open meeting confirmed inquirer when meeting cancelled
    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param caom_id:
        the row id of the ca_open_meeting
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            caom = CAOpenMeeting.query.get(caom_id)
            if not caom:
                return True
            message_name['event_name'] = caom.title
            if caom.slots:
                slot_ids = [s.row_id for s in caom.slots]
                for slot_id in slot_ids:
                    # slot inquirers details
                    slot_inquirers = CAOpenMeetingInquiry.query.filter_by(
                        ca_open_meeting_id=caom_id,
                        ca_open_meeting_slot_id=slot_id,
                        status=INQUIRIES.CONFIRMED).all()
                    slot_inquirer_user_ids = [
                        si.created_by for si in slot_inquirers]

                    for slot_inquirer_user_id in slot_inquirer_user_ids:
                        slot_inquirer_user = User.query.filter_by(
                            row_id=slot_inquirer_user_id).first()
                        if slot_inquirer_user:
                            json_data['user_id'] = slot_inquirer_user.row_id
                            json_data['account_id'] = \
                                slot_inquirer_user.account_id
                            json_data['notification_group'] = \
                                NOTIFY.NGT_CA_OPEN_MEETING
                            json_data['notification_type'] = sub_type
                            json_data['ca_open_meeting_id'] = caom_id
                            # check if already notification generated for
                            # particular user
                            if Notification.query.filter(and_(
                                    Notification.user_id ==
                                    slot_inquirer_user.row_id,
                                    Notification.account_id ==
                                    slot_inquirer_user.account_id,
                                    Notification.notification_group ==
                                    NOTIFY.NGT_CA_OPEN_MEETING,
                                    Notification.notification_type == sub_type,
                                    Notification.ca_open_meeting_id ==
                                    caom_id)).first():
                                continue

                            data, errors = NotificationSchema().load(json_data)
                            if errors:
                                return True
                            db.session.add(data)
                            db.session.commit()
                            # emit notification to user
                            notify_user = slot_inquirer_user
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
                                'notification_group':
                                NOTIFY.NGT_CA_OPEN_MEETING,
                                'notification_type': sub_type},
                                namespace=SOCKETAPP.NS_NOTIFICATION,
                                room=notify_user.get_room_id(
                                room_type=SOCKETAPP.NS_NOTIFICATION))
                            # send push notification for user
                            if (notify_user.settings.
                                    android_request_device_ids or
                                    notify_user.settings.
                                    ios_request_device_ids):
                                data = {
                                    "content_available": True,
                                    "priority": "high",
                                    "show_in_foreground": True,
                                    "data": {
                                        "body": NOTIFY.NOTIFICATION_MESSAGES[
                                                    sub_type] % message_name,
                                        "title": current_app.config[
                                            'BRAND_NAME'],
                                        "user_id": data.user_id,
                                        "notification_row_id": data.row_id,
                                        "redirect_row_id": caom.row_id,
                                        "notification_group":
                                            NOTIFY.NGT_CA_OPEN_MEETING,
                                        "notification_type": sub_type,
                                        "sound": "default",
                                        "click_action": "FCM_PLUGIN_ACTIVITY",
                                        "icon": "icon"
                                    }
                                }
                                if notify_user.settings.\
                                        android_request_device_ids:
                                    data['registration_ids'] = \
                                        notify_user.settings.\
                                        android_request_device_ids
                                    android_response = push_notification(data)
                                if notify_user.settings.ios_request_device_ids:
                                    data['registration_ids'] = \
                                        notify_user.settings. \
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
