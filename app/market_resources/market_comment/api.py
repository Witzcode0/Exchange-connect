"""
API endpoints for "market comment API" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from flasgger import swag_from
from sqlalchemy import and_
from sqlalchemy import Date, cast

from app import db, c_abort, corporateannouncementfile
from app.base.api import AuthResource
from app.market_resources.market_comment.models import (
    MarketAnalystComment)
from app.market_resources.market_comment.schemas import (
    MarketanalystCommentSchema, MarketanalystCommentReadArgsSchema)
from app.resources.users.models import User
from app.resources.accounts.models import Account


class MarketCommentAPI(AuthResource):
    """
    For creating Market Comment 
    """

    def post(self):
        """
        Create Market Comment
        """
        analyst_comment_schema = MarketanalystCommentSchema()
        # get the form data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = analyst_comment_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Market Comment Created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update market comment
        """
        analyst_comment_schema = MarketanalystCommentSchema()
        model = None
        try:
            model = MarketAnalystComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Market Comment id: %s'
                                     ' does not exist' % str(row_id))

            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
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
            data, errors = analyst_comment_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Market Comment id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a Market Comment
        """
        model = None
        try:
            # first find model
            model = MarketAnalystComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Market Comment id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
                abort(403)
            # if model is found, and not yet deleted, delete it
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

    def get(self, row_id):
        """
        Get a Market Comment request by id
        """
        model = None
        try:
            # first find model
            model = MarketAnalystComment.query.get(row_id)
            if model is None:
                c_abort(404, message='Market Comment id: %s'
                                     ' does not exist' % str(row_id))
            result = MarketanalystCommentSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class MarketCommentListAPI(AuthResource):
    """
    Read API for market comment lists, i.e, more than 1
    """
    model_class = MarketAnalystComment

    def __init__(self, *args, **kwargs):
        super(MarketCommentListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        date = None
        if 'created_date' in filters:
            date = filters.pop('created_date')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass

        if date:
            query_filters['base'].append(
                cast(MarketAnalystComment.created_date,Date) == date)

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.options(
            joinedload(MarketAnalystComment.creator).load_only(
                'row_id', 'account_id').joinedload(
                User.account).joinedload(Account.profile))

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            MarketanalystCommentReadArgsSchema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(MarketAnalystComment),
                                 operator)
            # making a copy of the main output schema
            comment_schema = MarketanalystCommentSchema(
                exclude=MarketanalystCommentSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                comment_schema = MarketanalystCommentSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Market Comment found')
            result = comment_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
