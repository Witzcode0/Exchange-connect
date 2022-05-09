"""
Socket events for "notifications" socket
"""

from app.auth.decorators import socket_authenticated_only

from socketapp.base.events import BaseNamespace


class NotificationsNamespace(BaseNamespace):
    """
    All event handlers for /notifications namespace
    """

    def on_connect(self):
        super(NotificationsNamespace, self).on_connect()

    def on_disconnect(self):
        super(NotificationsNamespace, self).on_disconnect()

    @socket_authenticated_only
    def on_join(self, message):
        super(NotificationsNamespace, self).on_join(message)

    @socket_authenticated_only
    def on_leave(self, message):
        super(NotificationsNamespace, self).on_leave(message)

    @socket_authenticated_only
    def on_close_room(self, message):
        super(NotificationsNamespace, self).on_close_room(message)
