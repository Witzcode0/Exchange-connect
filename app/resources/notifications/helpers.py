"""
Helper classes/functions for "notifications" package.
"""
from flask import current_app

from app import db, sockio
from app.resources.notifications.schemas import NotificationSchema
from app.resources.users.models import User
from socketapp.base import constants as SOCKETAPP


class NotificationMessage(object):
    """
    # #TODO: maybe implement in future
    Notification message builder
    """

    def __init__(self, *args, **kwargs):
        super(NotificationMessage, self).__init__(*args, **kwargs)


def add_notification(user_id, account_id, notify_grp, notify_type,
                     designlab_notification=False, **kwargs):
    """
     adds notification, updates current notification count of user
     and emits the notification
    :param user_id: int
    :param account_id: int
    :param notify_grp: str
    :param notify_type: str
    :param kwargs: other column in notifications
    :return:
    """
    json_data = {
        "user_id": user_id,
        "account_id": account_id,
        "notification_group": notify_grp,
        "notification_type": notify_type}
    json_data.update(kwargs)
    data, errors = NotificationSchema().load(json_data)
    if errors:
        return True
    db.session.add(data)
    user = User.query.get(user_id)
    user.current_notification_count += 1
    db.session.add(user)
    db.session.commit()
    if designlab_notification:
        sockio.emit('new_notification', {
            'user_id': data.user_id,
            'notification_row_id': data.row_id,
            'notification_group': data.notification_group,
            'notification_type': data.notification_type},
            namespace=SOCKETAPP.NS_DESIGNLAB_NOTIFICATION,
            room=user.get_room_id(
            room_type=SOCKETAPP.NS_DESIGNLAB_NOTIFICATION))
    else:
        sockio.emit('new_notification', {
            'user_id': data.user_id,
            'notification_row_id': data.row_id,
            'notification_group': data.notification_group,
            'notification_type': data.notification_type},
            namespace=SOCKETAPP.NS_NOTIFICATION,
            room=user.get_room_id(
            room_type=SOCKETAPP.NS_NOTIFICATION))
