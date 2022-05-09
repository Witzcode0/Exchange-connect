from flask import current_app

from app import db, sockio
from app.common.utils import push_notification
from app.resources.follows.models import CFollow
from app.resources.notifications.models import Notification
from app.resources.notifications.schemas import NotificationSchema
from app.resources.users.models import User
from app.resources.notifications import constants as NOTIFY
from queueapp.tasks import celery_app, logger
from socketapp.base import constants as SOCKETAPP
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.accounts.models import Account


@celery_app.task(bind=True, ignore_result=True)
def add_corporate_announcement_notification(self, result, row_id, sub_type, *args, **kwargs):
    """
        Adds a notification for admin announcement
        Notifies the admin announcement following users
    """
    if result:
        try:
            json_data = {}
            message_name = {}
            model = CorporateAnnouncement.query.get(row_id)

            if not row_id:
                return False
            account = db.session.query(Account) \
                .filter(Account.row_id == model.account_id).first()
            message_name['company'] = account.account_name
            message_name['announcement_title'] = model.subject
            users_list = db.session.query(CFollow.sent_by) \
                .filter(CFollow.company_id ==
                        model.account_id).all()

            if users_list:
                for user in users_list:
                    json_data['user_id'] = user[0]
                    json_data['account_id'] = \
                        model.account_id
                    json_data['notification_group'] = NOTIFY.NGT_ANNOUNCEMENT
                    json_data['notification_type'] = sub_type
                    json_data['c_announcement_id'] = row_id
                    data, errors = NotificationSchema().load(json_data)
                    if errors:
                        return False
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
                        'notification_group': NOTIFY.NGT_ANNOUNCEMENT,
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
                                "notification_group": NOTIFY.NGT_ANNOUNCEMENT,
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

            else:
                return False
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False
    print("notification added..")
    return result
