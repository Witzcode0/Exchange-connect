"""
Socket events for "feeds" socket
"""

from app.auth.decorators import socket_authenticated_only

from socketapp.base.events import BaseNamespace


class FeedsNamespace(BaseNamespace):
    """
    All event handlers for /feeds namespace
    """

    def on_connect(self):
        super(FeedsNamespace, self).on_connect()

    def on_disconnect(self):
        super(FeedsNamespace, self).on_disconnect()

    @socket_authenticated_only
    def on_join(self, message):
        super(FeedsNamespace, self).on_join(message)

    @socket_authenticated_only
    def on_leave(self, message):
        super(FeedsNamespace, self).on_leave(message)

    @socket_authenticated_only
    def on_close_room(self, message):
        super(FeedsNamespace, self).on_close_room(message)
