"""
Socket events for all sockets
"""

from flask import current_app, request, session, g
from flask_socketio import (
    Namespace, emit, join_room, leave_room, rooms, close_room)

from app.auth.decorators import socket_authenticated_only
from app.resources.users.models import User

from socketapp.base import constants as SOCKETAPP


class BaseNamespace(Namespace):
    """
    Common connect, ping and disconnect event handler
    """

    def on_connect(self):
        """
        Establish initial connection event
        """
        current_app.logger.exception('Connected: ' + str(request.sid))
        emit('connected', {'data': 'Connected', 'count': 1})

    def on_disconnect(self):
        """
        Disconnect socket connection event
        """
        current_app.logger.exception(
            'Client disconnected: ' + str(request.sid))

    def on_sock_ping(self):
        """
        Ping pong handler
        """
        emit('sock_pong', {'data': 'Still connected!', 'count': 0})

    def get_default_rooms(self):
        """
        Gets the default feed and notifications rooms from the current
        logged-in user
        """
        if not g or 'current_user' not in g:
            raise Exception('Cannot be called if current_user is '
                            'not populated')
        # get the user object, and its corresponding room ids
        user_obj = User.query.get(g.current_user['row_id'])
        if 'Origin' in request.headers:
            if 'designlab' in request.headers['Origin'].split(":")[1]:
                data = {'rooms': {
                    'feed': user_obj.get_room_id(),
                    'notification': user_obj.get_room_id(
                        room_type=SOCKETAPP.NS_DESIGNLAB_NOTIFICATION)}}
            else:
                data = {'rooms': {
                    'feed': user_obj.get_room_id(),
                    'notification': user_obj.get_room_id(
                        room_type=SOCKETAPP.NS_NOTIFICATION)}}
        else:
            data = {'rooms': {
                'feed': user_obj.get_room_id(),
                'notification': user_obj.get_room_id(
                    room_type=SOCKETAPP.NS_NOTIFICATION)}}
        return data

    @socket_authenticated_only
    def on_login(self, message):
        """
        Login after connect event
        """
        data = self.get_default_rooms()
        emit('login_success', data)

    @socket_authenticated_only
    def on_get_rooms(self, message):
        """
        Get the rooms (feed, notifications) for the user
        """
        data = self.get_default_rooms()
        emit('feed_notification_rooms', data)

    @socket_authenticated_only
    def on_join(self, message):
        join_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('joined_room',
             {'data': 'In rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})

    @socket_authenticated_only
    def on_leave(self, message):
        leave_room(message['room'])
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('left_room',
             {'data': 'Still in rooms: ' + ', '.join(rooms()),
              'count': session['receive_count']})

    @socket_authenticated_only
    def on_close_room(self, message):
        session['receive_count'] = session.get('receive_count', 0) + 1
        emit('closed_room',
             {'data': 'Room ' + message['room'] + ' is closing.',
              'count': session['receive_count']},
             room=message['room'])
        close_room(message['room'])
