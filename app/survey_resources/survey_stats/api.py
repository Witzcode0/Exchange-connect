"""
API endpoints for "survey stats" package.
"""

from werkzeug.exceptions import HTTPException
from flask import current_app, g
from flask_restful import abort
from sqlalchemy import DECIMAL
from sqlalchemy.sql import func, case, cast, and_
from sqlalchemy.sql.functions import coalesce
from flasgger.utils import swag_from

from app import db
from app.base.api import AuthResource
from app.survey_resources.surveys.models import Survey
from app.survey_resources.survey_responses.models import SurveyResponse
from app.survey_resources.survey_responses import constants as SURRES
from app.survey_resources.surveys import constants as SURVEY
from app.survey_resources.survey_stats.schemas import \
    SurveyStatsOverallSchema, SurveyStatsOverAllForInviteeUserSchema, \
    SurveyStatsOverAllReadArgsSchema
from app.resources.accounts import constants as ACCOUNT


class SurveyOverallStatsAPI(AuthResource):
    """
    Get API for managing survey stats overall
    """
    model_class = Survey

    def __init__(self, *args, **kwargs):
        super(SurveyOverallStatsAPI, self).__init__(
            *args, **kwargs)

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

        survey_response_query = None
        # build specific extra queries filters
        if extra_query:
            pass

        # stats for survey creator(Corporate user only)
        if g.current_user['account_type'] == ACCOUNT.ACCT_CORPORATE:
            # get survey stats for current user
            # for normal query
            query_filters['base'].append(
                Survey.created_by == g.current_user['row_id'])

            query = db.session.query(
                func.count(Survey.row_id).label('total_surveys'),
                func.count(case([(Survey.editable.is_(False), 1)])).label(
                    'total_published_surveys'))
            query = self._build_final_query(query_filters, query, operator)

            # current user's survey stats for survey responses
            survey_response_query = db.session.query(
                func.count(case([(
                    SurveyResponse.status == SURRES.ANSWERED, 1)])).label(
                    'total_responses'),
                func.count(SurveyResponse.row_id).label('total_invitees'),
                cast((coalesce(func.count(case([(
                    SurveyResponse.status ==
                    SURRES.ANSWERED, 1)])) / func.nullif(
                        cast(query[0].total_published_surveys, DECIMAL(
                            precision=10, scale=2)), 0), 0)),
                    DECIMAL(precision=10, scale=2)).label(
                    'average_response_per_survey')).join(
                Survey, Survey.row_id == SurveyResponse.survey_id)
            survey_response_query = self._build_final_query(
                query_filters, survey_response_query, operator)
        else:
            # for guest user
            if g.current_user['account_type'] == ACCOUNT.ACCT_GUEST:
                query = db.session.query(
                    func.count(case([(Survey.editable.is_(False), 1)])).label(
                        'total_invited_surveys'),
                    func.count(case([(
                        Survey.status == SURVEY.RUNNING, 1)])).label(
                        'total_live_surveys'),
                    func.count(case([(
                        Survey.status == SURVEY.CLOSED, 1)])).label(
                        'total_completed_surveys')).join(
                    SurveyResponse, and_(
                        SurveyResponse.survey_id == Survey.row_id,
                        SurveyResponse.email == g.current_user['email'])
                )
            # for other user(sell-side, buy-side, general investor)
            else:
                query = db.session.query(
                    func.count(case([(Survey.editable.is_(False), 1)])).label(
                        'total_invited_surveys'),
                    func.count(case([(
                        Survey.status == SURVEY.RUNNING, 1)])).label(
                        'total_live_surveys'),
                    func.count(case([(
                        Survey.status == SURVEY.CLOSED, 1)])).label(
                        'total_completed_surveys')).join(
                    SurveyResponse, and_(
                        SurveyResponse.survey_id == Survey.row_id,
                        SurveyResponse.user_id == g.current_user['row_id'])
                )

            query = self._build_final_query(query_filters, query, operator)

        return query, survey_response_query

    def get(self):
        """
        Get survey stats overall
        """
        # making a copy of the main output schema
        survey_stats_schema = SurveyStatsOverallSchema()
        survey_stats_for_invitee_schema = \
            SurveyStatsOverAllForInviteeUserSchema()
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            SurveyStatsOverAllReadArgsSchema())
        try:
            # build the sql query
            query, survey_response_query =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Survey),
                                 operator)
            # run the survey_stats query
            survey_stats = query.first()
            survey_response_stats = survey_response_query
            # when stats for survey creator(corporate user)
            if survey_response_stats:
                survey_response_stats = survey_response_query.first()
                result = survey_stats_schema.dump(survey_stats)
                result.data.update(
                    survey_stats_schema.dump(
                        survey_response_stats).data)
            else:
                result = survey_stats_for_invitee_schema.dump(
                    survey_stats)

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data}, 200
