"""
API endpoints for "admin publish notifications" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.auth.decorators import role_permission_required
from app.base.api import AuthResource
from app.resources.admin_publish_notifications.models import \
    AdminPublishNotification
from app.resources.admin_publish_notifications.schemas import (
    AdminPublishNotificationSchema, AdminPublishNotificationReadArgsSchema)
from app.base import constants as APP
from app.resources.roles import constants as ROLE
from app.resources.notifications import constants as NOTIFY

from queueapp.notification_tasks import add_admin_publish_notifications


class AdminPublishNotificationAPI(AuthResource):
    """
    CRUD API for managing admin publish
    notification
    """

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_AD])
    def post(self):
        """
        Create an admin publish notification
        """
        admin_publish_notification_schema = AdminPublishNotificationSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = admin_publish_notification_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # send notification
            add_admin_publish_notifications.s(
                True, data.row_id, NOTIFY.NT_ADMIN_PUBLISH_NOTIFICATION
            ).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'AdminPublishNotification added: %s' % str(
            data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_AD])
    # @swag_from('swagger_docs/admin_publish_notification_delete.yml')
    def delete(self, row_id):
        """
        Delete an admin_publish_notification by id
        """
        model = None
        try:
            # first find model
            model = AdminPublishNotification.query.get(row_id)
            if model is None:
                c_abort(404, message='AdminPublishNotification id: %s does '
                                     'not exist' % str(row_id))

            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_AD])
    # @swag_from('swagger_docs/admin_publish_notification_get.yml')
    def get(self, row_id):
        """
        Get an admin publish notification by id
        """
        model = None
        try:
            # first find model
            model = AdminPublishNotification.query.get(row_id)
            if model is None:
                c_abort(404, message='AdminPublishNotification id: %s does '
                                     'not exist' % str(row_id))
            result = AdminPublishNotificationSchema(
                exclude=AdminPublishNotificationSchema._default_exclude_fields
            ).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AdminPublishNotificationListAPI(AuthResource):
    """
    Read API for admin publish notification lists, i.e, more than 1
    admin publish notification
    """
    model_class = AdminPublishNotification

    def __init__(self, *args, **kwargs):
        super(AdminPublishNotificationListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_AD])
    # @swag_from('swagger_docs/admin_publish_notification_get_list.yml')
    def get(self):
        """
        Get the list
        """
        admin_publish_notification_read_schema = \
            AdminPublishNotificationReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_publish_notification_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(AdminPublishNotification),
                                 operator)
            # making a copy of the main output schema
            admin_publish_notification_schema = AdminPublishNotificationSchema(
                exclude=AdminPublishNotificationSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_publish_notification_schema = \
                    AdminPublishNotificationSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching admin publish '
                                     'notification found')
            result = admin_publish_notification_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
