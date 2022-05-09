"""
API endpoints for "goal tracker" package.
"""

from werkzeug.exceptions import Forbidden
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import load_only
from marshmallow.exceptions import ValidationError
from sqlalchemy import and_, any_, func, or_

from app import db
from app.base.api import AuthResource
from app.activity.activities import constants as ACTIVITY
from app.activity.activities.models import Activity
from app.resources.goaltrackers.models import GoalTracker
from app.resources.goaltrackers.schemas import (
    GoalTrackerSchema, GoalTrackerReadArgsSchema, ActivitiesStatusSchema,
    validate_tracked_activities)
from app.resources.goaltrackers.helpers import goal_count_update

from queueapp.goaltracker_tasks import manage_goaltrackers_on_status_change
from app.resources.activity_type.models import ActivityType


# main input output schema of goal tracker
goal_tracker_schema = GoalTrackerSchema(strict=True)
# schema for reading get arguments
goal_tracker_read_schema = GoalTrackerReadArgsSchema(strict=True)
# schema for activities status update
activities_status_schema = ActivitiesStatusSchema(strict=True)


class GoalTrackerAPI(AuthResource):
    """
    Create,Update,Delete API for GoalTracker
    """

    def post(self):
        """
        create goal tracker
        :return:
        """
        # get json data from the request
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400

        try:
            # validate and deserialize data from request
            data, errors = goal_tracker_schema.load(json_data)
            if errors:
                return errors, 422
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            # update the counts, and completed activity ids first
            data.goal_count, data.completed_activity_ids = goal_count_update(
                data, request.method)

            db.session.add(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500

        return {'message': 'GoalTracker Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        for update goal tracker
        :return:
        """
        model = None
        try:
            model = GoalTracker.query.get(row_id)
            if model is None:
                return {
                    'message': 'GoalTracker id: %s does not exist' %
                    str(row_id)}, 404
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
        except Forbidden as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500

        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400

        try:
            data, errors = goal_tracker_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                return errors, 422
            # no errors, so add data to db
            # update the counts, and completed activity ids first
            data.goal_count, data.completed_activity_ids = goal_count_update(
                data, request.method)
            db.session.add(data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        return {'message': 'Updated GoalTracker id: %s' % str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete goaltracker
        :return:
        """
        model = None
        try:
            model = GoalTracker.query.get(row_id)
            if model is None:
                return {
                    'message': 'GoalTracker id: %s does not exist' %
                    str(row_id)}, 404
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)

            db.session.delete(model)
            db.session.commit()
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        return {}, 204

    def get(self, row_id):
        """
        get goaltracker
        :return:
        """
        model = None
        try:
            model = GoalTracker.query.get(row_id)
            if model is None:
                return {
                    'message': 'GoalTracker id: %s does not exist' %
                    str(row_id)}, 404
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = goal_tracker_schema.dump(model)
        except Forbidden as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500

        return {'results': result}, 200


class GoalTrackerList(AuthResource):
    """
    Fetch more than one goaltracker List
    """
    model_class = GoalTracker

    def __init__(self, *args, **kwargs):
        super(GoalTrackerList, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
         Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        # build the default queries, using the parent helper
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        # build specific extra queries
        if extra_query:
            mapper = inspect(self.model_class)
            for f in extra_query:
                if 'activity_name' in extra_query and extra_query['activity_name']:
                    activity_name = '%' + (extra_query["activity_name"]).lower() + '%'
                    query_filters['filters'].append(
                        func.lower(ActivityType.activity_name).like(activity_name))

        query_filters['base'].append(
            GoalTracker.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        user_query = query.join(
            ActivityType, ActivityType.row_id == GoalTracker.activity_type)

        if sort:
            for col in sort['sort_by']:
                if col == 'activity_name':
                    mapper = inspect(ActivityType)
                    col = 'activity_name'
                    sort_fxn = 'asc'
                    if sort['sort'] == 'dsc':
                        sort_fxn = 'desc'
                    order.append(getattr(mapper.columns[col], sort_fxn)())

        return user_query, db_projection, s_projection, order, paging

    def get(self):
        """
        get the list
        :return:
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            goal_tracker_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(GoalTracker), operator)
            # making a copy of the main output schema
            goaltracker_schema = GoalTrackerSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                goaltracker_schema = GoalTrackerSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                return {'message': 'No matching goal trackers found'}, 404
            result = goaltracker_schema.dump(models, many=True)
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500
        return {'results': result.data, 'total': total}, 200


class MultiActivityStatusUpdateAPI(AuthResource):
    """
    for update Activity Status
    """

    def put(self, row_id):
        """
        For update activity status for completed Activity ids and
        incomplete Activity ids
        """
        model = None
        try:
            model = GoalTracker.query.get(row_id)
            if model is None:
                return {
                    'message': 'GoalTracker id: %s does not exist' %
                    str(row_id)}, 404
        except Exception as e:
            current_app.logger.exception(e)
            return {}, 500

        # get json data from the request
        json_data = request.get_json()
        if not json_data:
            return {'message': 'No input data provided'}, 400

        try:
            # validate and deserialize data from request
            data, errors = activities_status_schema.load(json_data)
            if not errors:
                # extra validation of correct activity ids being sent
                model.load_tracked_activities()
                errors = validate_tracked_activities(data, model)
            if errors:
                return errors, 422
            # no errors, so add data to db
            # update activity statuses
            if 'completed_ids' in data and data['completed_ids']:
                Activity.query.filter(
                    Activity.row_id.in_(data['completed_ids'])).update({
                        Activity.status: ACTIVITY.EST_CD},
                        synchronize_session=False)
                db.session.commit()
            if 'incomplete_ids' in data and data['incomplete_ids']:
                # #TODO: for now setting incomplete as None
                Activity.query.filter(
                    Activity.row_id.in_(data['incomplete_ids'])).update({
                        Activity.status: None}, synchronize_session=False)
                db.session.commit()
            # update goal count
            model.goal_count, model.completed_activity_ids = goal_count_update(
                model)
            db.session.add(model)
            db.session.commit()
            # update counts for other possible goals that match the activities
            manage_goaltrackers_on_status_change.s(
                True, row_id, data['completed_ids'],
                data['incomplete_ids']).delay()
        except ValidationError as e:
            return e.messages, 422
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            return {}, 500
        return {'message': 'Activity Status Updated'}, 200
