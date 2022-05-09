"""
 API for result-tracker
"""
import json
from http.client import HTTPException

from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import inspect, and_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from werkzeug.exceptions import Forbidden

from app.base import constants as APP

from app import c_abort, db
from app.base.api import AuthResource
from app.resources.result_tracker.models import ResultTrackerGroup
from app.resources.result_tracker.schemas import ResultTrackerGroupSchema, ResultTrackerGroupArgsSchema
from app.resources.result_tracker_companies.models import ResultTrackerGroupCompanies


class ResultTrackerGroupAPI(AuthResource):
    """
    post request to create new group
    """

    def post(self):
        """
        Create result tracker group
        """
        result_tracker_group_schema = ResultTrackerGroupSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            top_seq_id_group_company = ResultTrackerGroup.query. \
                filter(ResultTrackerGroup.user_id == g.current_user['row_id']). \
                order_by(ResultTrackerGroup.sequence_id.desc()).first()

            duplicate_case_sensitive = db.session.query(ResultTrackerGroup).filter(func.lower(
                ResultTrackerGroup.group_name) == json_data['group_name'].lower()).first()

            if duplicate_case_sensitive:
                return {'message': 'Already exists'}, 422

            json_data['sequence_id'] = 1 if not top_seq_id_group_company \
                else top_seq_id_group_company.sequence_id + 1

            data, errors = result_tracker_group_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.user_id = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                column: [APP.MSG_ALREADY_EXISTS]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Result tracker group created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update Result-Tracker group
        """

        result_tracker_group_schema = ResultTrackerGroupSchema()
        model = None
        try:
            model = ResultTrackerGroup.query.get(row_id)

            if model is None:
                c_abort(404, message='Result Tracker group id: %s'
                                     ' does not exist' % str(row_id))
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
            data, errors = result_tracker_group_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                column: [APP.MSG_ALREADY_EXISTS]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Result Tracker group id: %s' %
                           str(row_id)}, 200

    def get(self, row_id):
        """
        Get a result tracker group request by id
        """
        result_tracker_group_schema = ResultTrackerGroupSchema()
        model = None
        try:
            # first find model
            model = ResultTrackerGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Result Tracker group id: %s'
                                     ' does not exist' % str(row_id))
            result = result_tracker_group_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    def delete(self, row_id):
        """
        Delete a result tracker group
        """
        model = None
        try:
            # first find model
            model = ResultTrackerGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Result Tracker Group id: %s'
                                     ' does not exist' % str(row_id))

            top_seq_id_group = ResultTrackerGroup.query.order_by(ResultTrackerGroup.sequence_id.desc()).first()
            if model.row_id == top_seq_id_group.row_id:
                db.session.delete(model)
                group_companies = ResultTrackerGroupCompanies.query.filter(and_(
                    ResultTrackerGroupCompanies.group_id == model.row_id,
                    ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])).all()
                for each_company in group_companies:
                    db.session.delete(each_company)
                db.session.commit()
            else:
                result_tracker_groups = ResultTrackerGroup.query.filter(
                    ResultTrackerGroup.user_id == g.current_user['row_id']).all()
                for each_group in result_tracker_groups:
                    if each_group.sequence_id == model.sequence_id:
                        db.session.delete(model)
                        continue
                    if each_group.sequence_id > model.sequence_id:
                        each_group.sequence_id -= 1
                        db.session.add(each_group)
                group_companies = ResultTrackerGroupCompanies.query.filter(and_(
                    ResultTrackerGroupCompanies.group_id == model.row_id,
                    ResultTrackerGroupCompanies.user_id == g.current_user['row_id'])).all()
                for each_company in group_companies:
                    db.session.delete(each_company)
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


class ResultTrackerGroupListAPI(AuthResource):
    """
    Read API for Result Tracker Group lists, i.e, more than 1 Group
    """
    model_class = ResultTrackerGroup

    def __init__(self, *args, **kwargs):
        super(
            ResultTrackerGroupListAPI, self).__init__(*args, **kwargs)

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
        mapper = inspect(ResultTrackerGroup)
        # build specific extra queries filters
        account_id = None

        query = self._build_final_query(
            query_filters, query_session, operator)

        query = query.filter(ResultTrackerGroup.user_id == g.current_user['row_id'])

        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list of Result Tracker Group
        """
        # schema for reading get arguments
        result_tracker_group_schema = ResultTrackerGroupArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            result_tracker_group_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ResultTrackerGroup),
                                 operator)

            # making a copy of the main output schema
            result_group_schema = ResultTrackerGroupSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                result_group_schema = ResultTrackerGroupSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                return {'message': 'No matching Result Tracker Group found'}, 404
            result = result_group_schema.dump(models, many=True)

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ResultTrackerGroupBulkAPI(AuthResource):
    """
    For update bulk result groups
    """

    def put(self):
        """
        Update result groups
        """
        result_tracker_group_schema = ResultTrackerGroupSchema()
        model = None

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        group_list = json_data['watchlist']
        try:
            for group in group_list:

                if "row_id" in group.keys():
                    model = ResultTrackerGroup.query.get(group["row_id"])
                    if model is None:
                        c_abort(404, message='Result Tracker Group id: %s'
                                             ' does not exist' % str(group["row_id"]))

                    data, errors = result_tracker_group_schema.load(
                        group, instance=model, partial=True)
                    if errors:
                        c_abort(422, errors=errors)
                    # no errors, so add data to db
                    db.session.add(data)
                    db.session.commit()

        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Result Tracker groups are updated'}, 200
