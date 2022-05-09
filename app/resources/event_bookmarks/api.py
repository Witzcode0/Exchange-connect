"""
API endpoints for "event bookmark" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from
from sqlalchemy.inspection import inspect

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.event_bookmarks.models import EventBookmark
from app.resources.event_bookmarks.schemas import (
    EventBookmarkSchema, EventBookmarkReadArgsSchema)
from app.resources.events.models import Event
from app.resources.event_types.models import EventType
from app.base import constants as APP


# main schema for input and output
event_bookmark_schema = EventBookmarkSchema()
# schema for reading get arguments
event_bookmark_read_schema = EventBookmarkReadArgsSchema(strict=True)


class EventBookmarkAPI(AuthResource):
    """
    Create, delete, get API for event bookmark
    """

    @swag_from('swagger_docs/event_bookmark_post.yml')
    def post(self):
        """
        Create event bookmark
        """
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        model = None
        try:
            # validate and deserialize input into object
            data, errors = event_bookmark_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            model = Event.query.filter(Event.row_id == data.event_id).first()
            if model is None or model.deleted:
                c_abort(404, message='Event id: %s does not exist' %
                                     str(data.event_id))

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']

            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (created_by, event_id)=(2, 6) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'EventBookmark added %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/event_bookmark_delete.yml')
    def delete(self, row_id):
        """
        Delete event bookmark by id
        """
        model = None
        try:
            model = EventBookmark.query.get(row_id)
            if model is None:
                c_abort(404, message='EventBookmark id: %s does not exist' %
                                     str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(403)

            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {}, 204

    @swag_from('swagger_docs/event_bookmark_get.yml')
    def get(self, row_id):
        """
        Get event bookmark by id
        """
        model = None
        try:
            model = EventBookmark.query.get(row_id)
            if model is None:
                c_abort(404, message='EventBookmark id: %s does not exist' %
                                     str(row_id))
            result = event_bookmark_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class EventBookmarkListAPI(AuthResource):
    """
    Read API for event bookmark lists, i.e, more than one
    """

    model_class = EventBookmark

    def __init__(self, *args, **kwargs):
        super(EventBookmarkListAPI, self).__init__(*args, **kwargs)

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
        mapper = inspect(Event)
        # build specific extra queries filters
        if extra_query:
            for f in extra_query:
                # dates
                if f in ['start_date_from', 'start_date_to',
                         'end_date_from', 'end_date_to'] and extra_query[f]:
                    # get actual field name
                    fld = f.replace('_from', '').replace('_to', '')
                    # build date query
                    if '_from' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] >= filters[f])
                        continue
                    if '_to' in f:
                        query_filters['filters'].append(
                            mapper.columns[fld] <= filters[f])
                        continue
                elif f == 'event_type':
                    query_filters['filters'].append(
                        EventType.name == extra_query[f])
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        if 'event_id' not in filters:
            query_filters['base'].append(
                EventBookmark.created_by == g.current_user['row_id'])

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.join(Event).join(EventType)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/event_bookmark_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            event_bookmark_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(EventBookmark), operator)
            # making a copy of the main output schema
            event_bookmark_schema = EventBookmarkSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                event_bookmark_schema = EventBookmarkSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching event bookmark found')
            result = event_bookmark_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
