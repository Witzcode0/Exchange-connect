from sqlalchemy.orm import load_only
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.resources.personalised_video_logs.models import PersonalisedVideoLogs
from app.resources.personalised_video_logs.schemas import PersonalisedVideoLogsSchema, PersonalisedVideoLogsReadArgsSchema


class PersonalisedVideoLogsAPI(AuthResource):
    def get(self, row_id):
        """
        Get Invitee by id
        """
        model = None
        try:
            model = PersonalisedVideoLogs.query.get(row_id)
            if model is None:
                c_abort(404, message='Invitee id: %s does not exist' %
                                     str(row_id))
            result = PersonalisedVideoLogsSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class PersonalisedVideoLogListAPI(AuthResource):
    """
        Read API for personalised video log lists, i.e, more than 1
        """
    model_class = PersonalisedVideoLogs

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['user']
        super(PersonalisedVideoLogListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(
            query_filters, query_session, operator)
        return query, db_projection, s_projection, order, paging

    # @role_permission_required(perms=[ROLE.EPT_AA], roles=[
    #     ROLE.ERT_SU, ROLE.ERT_CA])
    def get(self):
        """
        Get the list
        """
        total = 0
        # print(ass)
        personalised_video_log_read_schema = PersonalisedVideoLogsReadArgsSchema(
            strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            personalised_video_log_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(PersonalisedVideoLogs),
                                 operator)
            # making a copy of the main output schema
            personalised_video_log_schema = PersonalisedVideoLogsSchema()

            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                personalised_video_log_schema = PersonalisedVideoLogsSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching login logs found')

            result = personalised_video_log_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200