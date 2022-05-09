"""
API endpoints for "webcast hosts" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.webcast_resources.webcasts.models import Webcast
from app.webcast_resources.webcast_hosts.models import WebcastHost
from app.webcast_resources.webcast_hosts.schemas import (
    WebcastHostSchema, WebcastHostReadArgsSchema)
from queueapp.webcasts.stats_tasks import update_webcast_stats


class WebcastHostAPI(AuthResource):
    """
    CRUD API for managing webcast hosts
    """
    @swag_from('swagger_docs/webcast_hosts_post.yml')
    def post(self):
        """
        Create a webcast host
        """
        webcast_host_schema = WebcastHostSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = webcast_host_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webcast
            webcast = Webcast.query.get(data.webcast_id)
            if webcast.cancelled:
                c_abort(422, errors='Webcast cancelled,'
                        ' so you cannot add a host')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # update webcast stats
            update_webcast_stats.s(True, data.webcast_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id, host_id)=(3, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id)=(10) is not present in table "webcast".
                # Key (host_id)=(4) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Webcast Host added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webcast_hosts_put.yml')
    def put(self, row_id):
        """
        Update a webcast host
        """
        webcast_host_schema = WebcastHostSchema()
        # first find model
        model = None
        try:
            model = WebcastHost.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast Host id: %s does not exist' %
                        str(row_id))
            # old_webcast_id, to be used for stats calculation
            wc_id = model.webcast_id
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input
            data, errors = webcast_host_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webcast
            webcast = Webcast.query.get(model.webcast_id)
            if webcast.cancelled:
                c_abort(422, message='Webcast cancelled,'
                        ' so you cannot update a host')
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            if wc_id != model.webcast_id:
                # update webcast stats
                update_webcast_stats.s(True, model.webcast_id).delay()
                update_webcast_stats.s(True, wc_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id, host_id)=(3, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id)=(10) is not present in table "webcast".
                # Key (host_id)=(4) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Webcast Host id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/webcast_hosts_delete.yml')
    def delete(self, row_id):
        """
        Delete a webcast host
        """
        model = None
        try:
            # first find model
            model = WebcastHost.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast Host id: %s does not exist' %
                        str(row_id))
            # for cancelled webcast
            webcast = Webcast.query.get(model.webcast_id)
            if webcast.cancelled:
                c_abort(422, message='Webcast cancelled,'
                        ' so you cannot delete a host')
            # old_webcast_id, to be used for stats calculation
            wc_id = model.webcast_id
            db.session.delete(model)
            db.session.commit()
            # update webcast stats
            update_webcast_stats.s(True, wc_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/webcast_hosts_get.yml')
    def get(self, row_id):
        """
        Get a webcast host by id
        """
        model = None
        try:
            # first find model
            model = WebcastHost.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast Host id: %s does not exist' %
                        str(row_id))
            result = WebcastHostSchema(
                exclude=WebcastHostSchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebcastHostListAPI(AuthResource):
    """
    Read API for webcast host lists, i.e, more than 1 webcast host
    """
    model_class = WebcastHost

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['webcast', 'host', 'creator']
        super(WebcastHostListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/webcast_hosts_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webcast_host_read_schema = WebcastHostReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webcast_host_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebcastHost), operator)
            # making a copy of the main output schema
            webcast_host_schema = WebcastHostSchema(
                exclude=WebcastHostSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webcast_host_schema = WebcastHostSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching webcast hosts found')
            result = webcast_host_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
