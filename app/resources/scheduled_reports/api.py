"""
API endpoints for "scheduled reports" package.
"""
import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.scheduled_reports.models import (
    ScheduledReport, ScheduledReportLog)
from app.resources.scheduled_reports.schemas import (
    ScheduledReportSchema, ScheduledReportReadArgsSchema,
    ScheduledReportLogSchema)
from app.resources.scheduled_reports import constants as SCH_REPORT


class ScheduledReportAPI(AuthResource):
    """
    CRUD API for scheduled report
    """

    @swag_from('swagger_docs/scheduled_report_post.yml')
    def post(self):
        """
        Create scheduled report
        """

        scheduled_report_schema = ScheduledReportSchema()
        # get the form data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = scheduled_report_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            db.session.add(data)
            db.session.commit()
            data.calculate_next_at()
            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Scheduled Report created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/scheduled_report_put.yml')
    def put(self, row_id):
        """
        Update scheduled report
        """
        scheduled_report_schema = ScheduledReportSchema()
        model = None
        try:
            model = ScheduledReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Scheduled Report id: %s'
                                     ' does not exist' % str(row_id))

            if model.created_by != g.current_user['row_id']:
                c_abort(403)

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
            earlier_is_active = model.is_active
            # validate and deserialize input
            data, errors = scheduled_report_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            if not earlier_is_active and data.is_active:
                # user reactivated the scheduled report need to adjust next_at
                # adding cron time delta to overcome the condition when next at
                # is greater than current time but cron already executed
                cur_time = datetime.datetime.utcnow() + datetime.timedelta(days=5)
                min_next_at = (cur_time + datetime.timedelta(
                                   minutes=SCH_REPORT.CRON_TIME_INTERVAL))
                while data.next_at < min_next_at:
                    data.calculate_next_at()

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

        return {'message': 'Updated scheduled report id: %s' %
                           str(row_id)}, 200

    @swag_from('swagger_docs/scheduled_report_delete.yml')
    def delete(self, row_id):
        """
        Delete a scheduled report
        """
        try:
            # first find model
            model = ScheduledReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Scheduled Report id: %s'
                        ' does not exist' % str(row_id))

            if model.created_by != g.current_user['row_id']:
                c_abort(403)

            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
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

    @swag_from('swagger_docs/scheduled_report_get.yml')
    def get(self, row_id):
        """
        Get a scheduled report by id
        """
        result = None
        try:
            # first find model
            model = ScheduledReport.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Scheduled Report id: %s'
                                     ' does not exist' % str(row_id))
            result = ScheduledReportSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class ScheduledReportListAPI(AuthResource):
    """
    Read API for scheduled report lists, i.e, more than 1
    """
    model_class = ScheduledReport

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator']
        super(ScheduledReportListAPI, self).__init__(*args, **kwargs)

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

        query_filters['base'].append(
            ScheduledReport.created_by == g.current_user['row_id']
        )
        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/scheduled_report_getlist.yml')
    def get(self):
        """
        Get the list
        """
        total = 0
        scheduled_report_read_schema = ScheduledReportReadArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            scheduled_report_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ScheduledReport),
                                 operator)
            # making a copy of the main output schema
            scheduled_report_schema = ScheduledReportSchema(
                exclude=ScheduledReportSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                scheduled_report_schema = ScheduledReportSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching scheduled reports found')

            result = scheduled_report_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class ScheduledReportLogApi(AuthResource):

    @swag_from('swagger_docs/scheduled_report_log_post.yml')
    def post(self):
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        try:
            log = ScheduledReportLog.query.get(json_data['report_log_id'])
            if not log:
                c_abort(404, message='No matching scheduled report log found')
            log_schema = ScheduledReportLogSchema()
            data, errors = log_schema.load(
                json_data, instance=log, partial=True)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Log created for Scheduled Report id: {}'.format(
            data.report_id
        )}, 201
