"""
API endpoints for "webcast rsvps" package.
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
from app.webcast_resources.webcast_rsvps.models import WebcastRSVP
from app.webcast_resources.webcast_rsvps.schemas import (
    WebcastRSVPSchema, WebcastRSVPReadArgsSchema)
from app.webcast_resources.webcasts.models import Webcast
from queueapp.webcasts.stats_tasks import update_webcast_stats


class WebcastRSVPAPI(AuthResource):
    """
    CRUD API for managing webcast rsvp
    """
    @swag_from('swagger_docs/webcast_rsvps_post.yml')
    def post(self):
        """
        Create a webcast rsvp
        """
        webcast_rsvps_schema = WebcastRSVPSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = webcast_rsvps_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webcast
            webcast = Webcast.query.get(data.webcast_id)
            if webcast.cancelled:
                c_abort(422, errors='Webcast cancelled,'
                        ' so you cannot add rsvps')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # update webcast stats
            update_webcast_stats.s(True, data.webcast_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id)=(3) is not present in table "webcast".
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

        return {'message': 'Webcast RSVP added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webcast_rsvps_put.yml')
    def put(self, row_id):
        """
        Update a webcast rsvp
        """
        webcast_rsvps_schema = WebcastRSVPSchema()
        # first find model
        model = None
        try:
            model = WebcastRSVP.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast RSVP id: %s does not exist' %
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
            data, errors = webcast_rsvps_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webcast
            webcast = Webcast.query.get(model.webcast_id)
            if webcast.cancelled:
                c_abort(422, message='Webcast cancelled,'
                        'so you cannot update rsvps')
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
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webcast_id)=(3) is not present in table "webcast".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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
        return {'message': 'Updated Webcast RSVP id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/webcast_rsvps_delete.yml')
    def delete(self, row_id):
        """
        Delete a webcast rsvp
        """
        model = None
        try:
            # first find model
            model = WebcastRSVP.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast RSVP id: %s does not exist' %
                        str(row_id))
            # old_webcast_id, to be used for stats calculation
            wc_id = model.webcast_id
            # for cancelled webcast
            webcast = Webcast.query.get(wc_id)
            if webcast.cancelled:
                c_abort(422, message='Webcast cancelled,'
                        'so you cannot delete rsvps')
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

    @swag_from('swagger_docs/webcast_rsvps_get.yml')
    def get(self, row_id):
        """
        Get a webcast rsvp by id
        """
        webcast_rsvps_schema = WebcastRSVPSchema()
        model = None
        try:
            # first find model
            model = WebcastRSVP.query.get(row_id)
            if model is None:
                c_abort(404, message='Webcast RSVP id: %s does not exist' %
                        str(row_id))
            result = webcast_rsvps_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebcastRSVPListAPI(AuthResource):
    """
    Read API for webcast rsvp lists, i.e, more than 1 project
    """
    model_class = WebcastRSVP

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['webcast', 'creator']
        super(WebcastRSVPListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/webcast_rsvps_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webcast_rsvps_read_schema = WebcastRSVPReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webcast_rsvps_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebcastRSVP), operator)
            # making a copy of the main output schema
            webcast_rsvps_schema = WebcastRSVPSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webcast_rsvps_schema = WebcastRSVPSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching webcast rsvps found')
            result = webcast_rsvps_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
