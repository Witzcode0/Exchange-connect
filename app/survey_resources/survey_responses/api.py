"""
API endpoints for "survey response" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from webargs.flaskparser import parser
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy import and_
from flasgger import swag_from

from app import db, c_abort
from app.base.api import BaseResource, AuthResource
from app.base import constants as APP
from app.base.schemas import BaseCommonSchema
from app.common.helpers import verify_event_book_token
from app.survey_resources.survey_responses.models import SurveyResponse
from app.survey_resources.survey_responses.schemas import (
    SurveyResponseSchema, SurveyResponseReadArgsSchema)
from app.survey_resources.survey_responses import constants as SURVEYRESPONSE
from app.survey_resources.surveys.models import Survey
from app.survey_resources.surveys import constants as SURVEY

from queueapp.surveys.email_tasks import send_survey_completion_email


class SurveyResponseAPI(BaseResource):
    """
    Update and get API for survey response
    """

    @swag_from('swagger_docs/survey_response_put.yml')
    def put(self, row_id):
        """
        Update survey response by id
        """
        input_data = None
        survey_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        # survey response input and output schema
        survey_response_schema = SurveyResponseSchema()
        model = None
        try:
            # if verify token there, then guest user or normal user booked
            # particular survey
            if 'token' in input_data and input_data['token']:
                # verify token
                survey_data = verify_event_book_token(
                    input_data['token'], APP.EVNT_SURVEY)
                if survey_data:
                    # if current user is guest user
                    model = SurveyResponse.query.filter(
                        and_(
                            SurveyResponse.
                            survey_id == survey_data[
                                'event_id'],
                            SurveyResponse.row_id == survey_data[
                                'invite_id']
                        )).first()
                else:
                    c_abort(422, message='Token invalid', errors={
                        'token': ['Token invalid']})
            else:
                model = SurveyResponse.query.get(row_id)
            if model is None:
                c_abort(404, message='Survey Response id: %s does not exist' %
                                     str(row_id))
            # TODO :- only invited user can change survey response
            # if model.user_id != g.current_user['row_id']:
            #     c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = survey_response_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.edited = True
            db.session.add(data)
            db.session.commit()
            # close survey when all invitees have responded (answered)
            total_invites = SurveyResponse.query.filter(
                SurveyResponse.survey_id == model.survey_id).count()
            total_responses = SurveyResponse.query.filter(and_(
                SurveyResponse.status == SURVEYRESPONSE.ANSWERED,
                SurveyResponse.survey_id == model.survey_id)).count()
            if total_invites == total_responses:
                Survey.query.filter(Survey.row_id == model.survey_id).update({
                    Survey.status: SURVEY.CLOSED}, synchronize_session=False)
                db.session.commit()
            # check here survey is completed,
            # if completed then send email to survey creator
            if data.status == SURVEYRESPONSE.ANSWERED:
                send_survey_completion_email.s(True, data.row_id).delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (survey_id, email)=(76, s2@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (survey_id)=(9) is not present in table "survey".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                db.session.rollback()
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Survey Response id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/survey_response_get.yml')
    def get(self, row_id):
        """
        Get survey response by id
        """
        input_data = None
        survey_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
        # survey response input and output schema
        survey_response_schema = SurveyResponseSchema()
        model = None
        try:
            # if verify token there, then guest user or normal user booked
            # particular survey
            if 'token' in input_data and input_data['token']:
                # verify token
                survey_data = verify_event_book_token(
                    input_data['token'], APP.EVNT_SURVEY)
                if survey_data:
                    # if current user is guest user
                    model = SurveyResponse.query.filter(
                        and_(
                            SurveyResponse.
                            survey_id == survey_data[
                                'event_id'],
                            SurveyResponse.row_id == survey_data[
                                'invite_id']
                        )).first()
                else:
                    c_abort(422, message='Token invalid', errors={
                        'token': ['Token invalid']})
            else:
                model = SurveyResponse.query.get(row_id)
            if model is None:
                c_abort(404, message='Survey Response id: %s does not exist' %
                                     str(row_id))
            result = survey_response_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class SurveyResponseDeleteAPI(AuthResource):
    """
    Delete API for survey response
    """
    @swag_from('swagger_docs/survey_response_delete.yml')
    def delete(self, row_id):
        """
        Delete survey response by id
        """
        model = None
        try:
            model = SurveyResponse.query.get(row_id)
            if model is None:
                c_abort(404, message='Survey Response id: %s does not exist' %
                                     str(row_id))
            if (model.user_id != g.current_user['row_id'] and
                    model.survey.created_by != g.current_user['row_id']):
                c_abort(401)

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


class SurveyResponseListAPI(BaseResource):
    """
    Read API for survey response lists, i.e, more than 1 survey response
    """

    model_class = SurveyResponse

    def __init__(self, *args, **kwargs):
        super(SurveyResponseListAPI, self).__init__(*args, **kwargs)

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
        # build specific extra queries filters
        if extra_query:
            pass

        # #TODO: user filter used in future
        # query_filters['base'].append(
        #     SurveyResponse.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)
        # #TODO: eager load

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/survey_response_get_list.yml')
    def get(self):
        """
        Get the list
        """
        # schema response for reading get arguments
        survey_response_read_schema = SurveyResponseReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            survey_response_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(SurveyResponse), operator)
            # making a copy of the main output schema
            survey_response_schema = SurveyResponseSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                survey_response_schema = SurveyResponseSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching survey response found')
            result = survey_response_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
