"""
API endpoints for "notifications" package.
"""

import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from flask import current_app, g, request
from flask_restful import abort
from sqlalchemy import and_, or_
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.notifications.models import Notification
from app.resources.notifications import constants as NOTIFY
from app.resources.notifications.schemas import (
    NotificationSchema, NotificationReadArgsSchema)
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT
from app.resources.user_settings import constants as USERSET


class NotificationAPI(AuthResource):
    """
    Get API for notification
    """

    @swag_from('swagger_docs/notification_put.yml')
    def put(self, row_id):
        """
        Change notification
        :param row_id:
        :return:
        """
        model = None
        unread_count = 0
        try:
            model = Notification.query.get(row_id)
            if model is None:
                c_abort(404, message='Notification id: %s does not exist' %
                                     str(row_id))
            if model.user_id != g.current_user['row_id']:
                c_abort(403)
            # for update notification count in user
            if not model.read_time:
                if 'Origin' in request.headers:
                    if 'designlab' in request.headers['Origin'].split(":")[1]:
                        if g.current_user['current_notification_designlab_count']:
                            unread_count = \
                                g.current_user['current_notification_designlab_count'] - 1
                            User.query.filter(User.row_id == model.user_id).update(
                                {User.current_notification_designlab_count:
                                    unread_count}, synchronize_session=False)
                    else:
                        if g.current_user['current_notification_count']:
                            unread_count = \
                                g.current_user['current_notification_count'] - 1
                            User.query.filter(User.row_id == model.user_id).update(
                                {User.current_notification_count:
                                    unread_count}, synchronize_session=False)
                else:
                    if g.current_user['current_notification_count']:
                        unread_count = \
                            g.current_user['current_notification_count'] - 1
                        User.query.filter(User.row_id == model.user_id).update(
                            {User.current_notification_count:
                                unread_count}, synchronize_session=False)

                model.read_time = datetime.datetime.utcnow()
                db.session.add(model)
                db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Notification id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/notification_get.yml')
    def get(self, row_id):
        """
        Get notification by id
        """
        notification_item_schema = NotificationSchema()
        model = None
        try:
            model = Notification.query.get(row_id)
            if model is None:
                c_abort(404, message='Notification id: %s does not exist' %
                                     str(row_id))
            result = notification_item_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class NotificationListAPI(AuthResource):
    """
    Read API for notification lists, i.e, more than 1 notification
    """
    model_class = Notification

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'user', 'account', 'post', 'post_comment', 'post_star', 'cfollow',
            'contact', 'corporate_access_event', 'webcast', 'webinar',
            'survey', 'ca_open_meeting', 'ca_open_meeting_inquiry',
            'ca_open_meeting_slot', 'bse_announcement']
        super(NotificationListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # join outer
        innerjoin = False
        main_filter = None

        # build specific extra queries filters
        if extra_query:
            for f in extra_query:
                if f == 'main_filter':
                    main_filter = extra_query[f]

        # user filter
        query_filters['base'].append(
            Notification.user_id == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        # #TODO: eager load
        if not main_filter:
            # no filter apply
            final_query = query

        if main_filter == NOTIFY.GENERAL or request.user_agent.platform in [USERSET.MOB_IOS, USERSET.MOB_ANDROID]:
            # For filter out exchangeconnect notifications

            final_query = query.filter(
                Notification.notification_group.notin_(NOTIFY.PROJECT_GROUP))

        elif main_filter == NOTIFY.DESIGNLAB:
            # For filter out designlab notifications

            final_query = query.filter(
                Notification.notification_group.in_(NOTIFY.PROJECT_GROUP))

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/notification_get_list.yml')
    def get(self):
        """
        Get the list
        """
        notification_item_read_schema = NotificationReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            notification_item_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Notification), operator)
            # making a copy of the main output schema
            notification_item_schema = NotificationSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                notification_item_schema = NotificationSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            for m in full_query.items:
                if m.contact:
                    # also add the_other dynamic property
                    if g.current_user['row_id'] == m.contact.sender.row_id:
                        m.contact.the_other = m.contact.sendee
                    else:
                        m.contact.the_other = m.contact.sender
                models.append(m)
            total = full_query.total
            if not models:
                c_abort(404, message='No matching notification found')
            result = notification_item_schema.dump(models, many=True)
            # for unread notification count for current user
            if g.current_user["account_type"] == ACCOUNT.ACCT_ADMIN:
                unread_count = int(g.current_user[
                'current_notification_designlab_count']) + int(g.current_user[
                'current_notification_count'])
            else:
                if 'Origin' in request.headers:
                    if 'designlab' in request.headers['Origin'].split(":")[1]:
                        unread_count = g.current_user['current_notification_designlab_count']
                    else:
                        unread_count = g.current_user['current_notification_count']
                else:
                    unread_count = g.current_user['current_notification_count']
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total,
                'unread_count': unread_count}, 200


class AllNotificationsAsRead(AuthResource):
    """
    All notifications of the user will be marked as read
    """

    def post(self):
        try:
            user_id = g.current_user['row_id']
            current_time = datetime.datetime.utcnow()
            if 'Origin' in request.headers:
                if 'designlab' in request.headers['Origin'].split(":")[1]:

                    Notification.query.filter(and_(
                        Notification.user_id == user_id,
                        Notification.read_time.is_(None),
                        Notification.notification_group.in_(
                            (NOTIFY.NGT_EMEETING,
                            NOTIFY.NGT_DESIGN_LAB_PROJECT)))).update({
                            Notification.read_time: current_time},
                        synchronize_session=False)

                    User.query.filter(User.row_id == user_id).update({
                        User.current_notification_designlab_count: 0
                    }, synchronize_session=False)
                elif 'admin' in request.headers['Origin'].split(":")[1]:
                    a = Notification.query.filter(and_(
                        Notification.user_id == user_id,
                        Notification.read_time.is_(None))).update({
                            Notification.read_time: current_time
                        }, synchronize_session=False)

                    User.query.filter(User.row_id == user_id).update({
                        User.current_notification_count: 0,
                        User.current_notification_designlab_count: 0
                    }, synchronize_session=False)
                else:
                    Notification.query.filter(and_(
                        Notification.user_id == user_id,
                        Notification.read_time.is_(None),
                        Notification.notification_group.notin_(
                            (NOTIFY.NGT_EMEETING,
                            NOTIFY.NGT_DESIGN_LAB_PROJECT)))).update({
                            Notification.read_time: current_time},
                        synchronize_session=False)

                    User.query.filter(User.row_id == user_id).update({
                        User.current_notification_count: 0
                    }, synchronize_session=False)
            else:
                Notification.query.filter(and_(
                    Notification.user_id == user_id,
                    Notification.read_time.is_(None),
                    Notification.notification_group.notin_(
                        (NOTIFY.NGT_EMEETING,
                        NOTIFY.NGT_DESIGN_LAB_PROJECT)))).update({
                        Notification.read_time: current_time},
                    synchronize_session=False)

                User.query.filter(User.row_id == user_id).update({
                    User.current_notification_count: 0
                }, synchronize_session=False)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Marked all notifications as read'}, 200
