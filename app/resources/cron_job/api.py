"""
API endpoints for "cronjob" package.
"""
from datetime import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from
from crontab import CronTab

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.auth.decorators import role_permission_required
from app.resources.cron_job.models import CronJob
from app.resources.cron_job.schemas import (
    CronJobSchema,
    CronJobReadArgsSchema)
from app.base import constants as APP
from app.resources.cron_job import constants as CRONJOB
from app.resources.cron_job.helpers import convert_time_into_utc


class CronJobAPI(AuthResource):
    """
    Cron start API for managing Cronjob
    """

    def put(self, row_id):
        """
        Update an Cron
        """
        cron_schema = CronJobSchema()
        # first find model
        model = None
        try:
            model = CronJob.query.get(row_id)
            if model is None:
                c_abort(404, message='Cron-Job id: %s does not exist' %
                                     str(row_id))
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
            cron_time = None
            timezone = "00:00"
            try:
                if 'time' in json_data and json_data['time']:
                    cron_time = datetime.strptime(''.join(json_data['time'].rsplit(":",1)),'%H:%M:%S.%f%z')
                    timezone = cron_time.strftime("%Z")[4:]
            except:
                c_abort(422, message="Please enter valid time")

            json_data['cron_time'] = cron_time
            json_data['timezone'] = timezone

            data, errors = cron_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
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

        try:
            if not data.is_deactive:
                '''If cron job is active'''

                # remove existing cron
                cron = CronTab(user=data.cr_user)
                cron.remove_all(comment=data.cron_type)
                cron.write()

                # add cron with updated data
                job = cron.new(command=data.command, comment=data.cron_type)
                minutes = '*'
                hours = '*'
                day_of_month = data.day_of_month if data.day_of_month else '*'
                month = data.month if data.month else '*'
                day_of_week = data.day_of_week if data.day_of_week else '*'
                if data.time:
                    utc_time = convert_time_into_utc(data.time,data.timezone)
                    minutes = utc_time.strftime("%M")
                    hours = utc_time.strftime("%H")
                if data.each:
                    if data.each ==CRONJOB.EACH_MINUTES:
                        minutes = "*/"+minutes
                        hours = "*"
                    elif data.each == CRONJOB.EACH_HOURS:
                        hours = "*/"+hours
                        minutes = "*"

                timing_comment = minutes+' '+hours+' '+day_of_month+' '+month+' '+day_of_week
                job.setall(timing_comment)
                cron.write()
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': "cron job id: %s has been updated"%str(row_id)}, 200

    def get(self, row_id):
        """
        Get an Cronjob by id
        """
        model = None
        try:
            # first find model
            model = CronJob.query.get(row_id)
            if model is None:
                c_abort(404, message='Cron id: %s does not exist' %
                                     str(row_id))
            result = CronJobSchema(
                exclude=CronJobSchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

class CronActivity(AuthResource):
    """
    Cron stop API for managing Cronjob
    """

    def put(self, row_id):
        """
        Update an Cron
        """
        cron_schema = CronJobSchema()
        # first find model
        model = None
        try:
            model = CronJob.query.get(row_id)
            if model is None:
                c_abort(404, message='Cron-Job id: %s does not exist' %
                                     str(row_id))
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        try:
            cron = CronTab(user=model.cr_user)
            message = None
            if model.is_deactive:
                # start updated cron
                job = cron.new(command=model.command, comment=model.cron_type)
                minutes = '*'
                hours = '*'
                day_of_month = model.day_of_month if model.day_of_month else '*'
                month = model.month if model.month else '*'
                day_of_week = model.day_of_week if model.day_of_week else '*'
                if model.time:
                    utc_time = convert_time_into_utc(model.time,model.timezone)
                    minutes = utc_time.strftime("%M")
                    hours = utc_time.strftime("%H")
                if model.each:
                    if model.each ==CRONJOB.EACH_MINUTES:
                        minutes = "*/"+minutes
                        hours = "*"
                    elif model.each == CRONJOB.EACH_HOURS:
                        hours = "*/"+hours
                        minutes = "*"

                timing_comment = minutes+' '+hours+' '+day_of_month+' '+month+' '+day_of_week
                job.setall(timing_comment)
                cron.write()
                model.is_deactive = False
                db.session.add(model)
                db.session.commit()
                message = 'Actived'
            else:
                cron.remove_all(comment=model.cron_type)
                cron.write()
                model.is_deactive = True
                db.session.add(model)
                db.session.commit()
                message = 'Deactived'
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'is_deactive':model.is_deactive,'message': 'cron job id: %s has been %s' %
                (str(row_id),message)}, 200


class CronListAPI(BaseResource):
    """
    Read API for Cronjob lists, i.e, more than 1 Cron
    """
    model_class = CronJob

    def __init__(self, *args, **kwargs):
        super(CronListAPI, self).__init__(*args, **kwargs)

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

        apply_domain_filter = False
        if request.headers.get('Domain-Code'):
            apply_domain_filter = True

        query = self._build_final_query(
            query_filters, query_session, operator, apply_domain_filter=apply_domain_filter)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/country_get_list.yml')
    def get(self):
        """
        Get the list
        """
        cron_read_schema = CronJobReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            cron_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CronJob), operator)
            # making a copy of the main output schema
            cron_schema = CronJobSchema(
                exclude=CronJobSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                cron_schema = CronJobSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Cron-Jobs found')
            result = cron_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
