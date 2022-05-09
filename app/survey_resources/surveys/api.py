"""
API endpoints for "survey" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from webargs.flaskparser import parser
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, joinedload, contains_eager
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base.schemas import account_fields, BaseCommonSchema
from app.base import constants as APP
from app.common.helpers import verify_event_book_token
from app.survey_resources.surveys.models import Survey
from app.survey_resources.surveys.schemas import (
    SurveySchema, SurveyReadArgsSchema)
from app.survey_resources.surveys import constants as SURVEY
from app.survey_resources.survey_responses.models import SurveyResponse
from app.survey_resources.survey_responses.schemas import SurveyResponseSchema
from app.resources.users.models import User
from app.resources.notifications.models import Notification
from app.resources.accounts import constants as ACCOUNT

from queueapp.surveys.email_tasks import send_survey_launch_email
from queueapp.notification_tasks import add_survey_notifications


class SurveyAPI(AuthResource):
    """
    Create, update, delete API for survey
    """
    @swag_from('swagger_docs/survey_post.yml')
    def post(self):
        """
        Create post
        """
        # survey input and output schema
        survey_schema = SurveySchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = survey_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            # external invitees added here to survey response table
            if data.external_invitees:
                for external_invitee in data.external_invitees:
                    external_invitee.created_by = g.current_user['row_id']
                    external_invitee.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # manage invites
            invitee_ids = []
            email_ids = []
            if (survey_schema._cached_contact_users or
                    survey_schema._cached_emails):
                for ccu in survey_schema._cached_contact_users:
                    if ccu not in data.invitees:
                        db.session.add(SurveyResponse(
                            survey_id=data.row_id, user_id=ccu.row_id))
                        invitee_ids.append(ccu.row_id)
                for ce in survey_schema._cached_emails:
                    if ce not in data.invitees:
                        db.session.add(SurveyResponse(
                            survey_id=data.row_id, email=ce))
                        email_ids.append(ce)
                db.session.commit()
            # condition for sending emails, if satisfies send emails
            if data.editable is False:
                send_survey_launch_email.s(True, data.row_id).delay()
                # true specifies mail sending task is in queue
                data.is_in_process = True
                db.session.add(data)
                db.session.commit()
            if invitee_ids:
                add_survey_notifications.s(
                    True, data.row_id, invitee_ids).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (survey_id, email)=(76, s2@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Survey Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/survey_put.yml')
    def put(self, row_id):
        """
        Update survey by id
        """
        # survey input and output schema
        survey_schema = SurveySchema()
        # schema for updating external_invitee
        external_invitee_schema = SurveyResponseSchema()
        model = None

        try:
            model = Survey.query.get(row_id)
            if model is None:
                c_abort(404, message='Survey id: %s does not exist' %
                                     str(row_id))
            # editable status, to be used for sending email for survey launch
            old_editable = model.editable
            # only current user can change survey
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

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
            survey_status = model.status
            external_invitee_data = None  # for external invitees data
            if 'external_invitees' in json_data and \
                    json_data['external_invitees']:
                external_invitee_data = json_data.pop('external_invitees')
            data, errors = survey_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            if (survey_status != SURVEY.OPEN):
                if (survey_status == data.status):
                    c_abort(422, message='Survey cannot be modified as status'
                            ' is not open')

            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # manage survey invites list
            if (survey_schema._cached_contact_users or
                    'invitee_ids' in json_data) or (
                    survey_schema._cached_emails or
                    'email_ids' in json_data):
                # add new ones by checking users
                invitee_ids = []
                email_ids = []
                # remove old ones
                for oldinvite in data.invites[:]:
                    if (oldinvite.invitee not in
                            survey_schema._cached_contact_users):
                        if oldinvite in data.invites:
                            if oldinvite.user_id:
                                db.session.delete(oldinvite)
                for ccu in survey_schema._cached_contact_users:
                    if ccu not in data.invitees:
                        db.session.add(SurveyResponse(
                            survey_id=data.row_id, user_id=ccu.row_id))
                        invitee_ids.append(ccu.row_id)
                for ce in survey_schema._cached_emails:
                    if ce not in data.invitees:
                        db.session.add(SurveyResponse(
                            survey_id=data.row_id,
                            email=ce))
                        email_ids.append(ce)
                db.session.commit()

            # manage external_invitees
            external_invitee_model = None
            if external_invitee_data:
                for external_invitee in external_invitee_data:
                    # if webcast_invitee found, update the webcast_invitee
                    ext_invitee = None
                    if 'row_id' in external_invitee:
                        external_invitee_model = SurveyResponse.query.get(
                            external_invitee['row_id'])
                        if not external_invitee_model:
                            db.session.rollback()
                            c_abort(404, message='External invitee '
                                                 'id: %s does not exist' %
                                                 str(external_invitee['row_id']
                                                     ))
                        ext_invitee, errors = \
                            external_invitee_schema.load(
                                external_invitee,
                                instance=external_invitee_model, partial=True)
                        if errors:
                            db.session.rollback()
                            c_abort(422, errors=errors)
                    else:
                        # if external_invitee row_id not present,
                        # add external_invitee
                        external_invitee['survey_id'] = data.row_id
                        # validate and deserialize input
                        ext_invitee, errors = (
                            external_invitee_schema.load(external_invitee))
                        if errors:
                            c_abort(422, errors=errors)
                        # no errors, so add external_invitees data to db
                    db.session.add(ext_invitee)
                db.session.commit()
            # condition for sending emails, if satisfies send emails
            if old_editable is True and model.editable is False:
                send_survey_launch_email.s(True, data.row_id).delay()
                # true specifies mail sending task is in queue
                data.is_in_process = True
                db.session.add(data)
                db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (survey_id, email)=(76, s2@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
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

        return {'message': 'Updated Survey id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/survey_delete.yml')
    def delete(self, row_id):
        """
        Delete survey by id
        """
        model = None
        try:
            model = Survey.query.get(row_id)
            if model is None:
                c_abort(404, message='Survey id: %s does not exist' %
                                     str(row_id))
            if model.created_by != g.current_user['row_id']:
                c_abort(401)

            # deleting responses from survey responses
           # SurveyResponse.query.filter(
           #     SurveyResponse.survey_id == row_id).delete()
            # deleting notifications
            Notification.query.filter(
                Notification.survey_id == row_id).delete()
            SurveyResponse.query.filter(SurveyResponse.survey_id == row_id).delete()
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

    @swag_from('swagger_docs/survey_get.yml')
    def get(self, row_id):
        """
        Get survey by id
        """
        model = None
        try:
            model = Survey.query.filter(Survey.row_id == row_id).join(
                SurveyResponse, and_(
                    SurveyResponse.survey_id == Survey.row_id, or_(
                        SurveyResponse.user_id == g.current_user['row_id'],
                        SurveyResponse.email == g.current_user['email'])),
                isouter=True).options(
                    contains_eager(Survey.invited)).first()
            if model is None:
                c_abort(404, message='Survey id: %s does not exist' %
                                     str(row_id))
            result = SurveySchema(
                exclude=SurveySchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class SurveyListAPI(AuthResource):
    """
    Read API for survey lists, i.e, more than 1 "Survey"
    """

    model_class = Survey

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = [
            'creator', 'account', 'invites', 'invited', 'invitees',
            'respondents', 'non_respondents', 'external_invitees']
        super(SurveyListAPI, self).__init__(*args, **kwargs)

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

        # for union query without current_user filter
        query_filters_union = {}
        query_filters_union['base'] = query_filters['base'][:]
        query_filters_union['filters'] = query_filters['filters'][:]
        # is_draft False filter for participated, invited etc
        query_filters_union['base'].append(
            Survey.editable.is_(False))
        query_for_union = self._build_final_query(
            query_filters_union, query_session, operator)

        # for normal query
        query_filters['base'].append(
            Survey.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        join_load = [
            contains_eager(Survey.invited),
            # invitees and contains_eager stuff
            joinedload(Survey.invitees).load_only(
                'row_id', 'account_id').joinedload(
                User.account).load_only(*account_fields),
            joinedload(Survey.invitees).load_only(
                'row_id').joinedload(User.profile)]

        # eager load
        query = query.options(*join_load)

        query_union = query_for_union.join(SurveyResponse, and_(
            SurveyResponse.survey_id == Survey.row_id, or_(
                SurveyResponse.user_id == g.current_user['row_id'],
                SurveyResponse.email == g.current_user['email']))).options(
                    *join_load)

        final_query = query.union(query_union)
        # join for survey invited
        final_query = final_query.join(SurveyResponse, and_(
            SurveyResponse.survey_id == Survey.row_id, or_(
                SurveyResponse.user_id == g.current_user['row_id'],
                SurveyResponse.email == g.current_user['email'])),
            isouter=True)

        return final_query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/survey_get_list.yml')
    def get(self):
        """
        Get the list
        """
        # schema for reading get arguments
        survey_read_schema = SurveyReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            survey_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Survey), operator)
            # making a copy of the main output schema
            survey_schema = SurveySchema(
                exclude=SurveySchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                survey_schema = SurveySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching surveys found')
            result = survey_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200


class SurveyGetAPI(BaseResource):
    """
    API for get survey for guest user
    """

    @swag_from('swagger_docs/survey_get_token.yml')
    def get(self, row_id):
        """
        Get survey by id
        """
        input_data = None
        survey_data = None
        input_data = parser.parse(
            BaseCommonSchema(), locations=('querystring',))
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
                    model = Survey.query.filter(Survey.row_id == survey_data[
                        'event_id']).join(SurveyResponse, and_(
                            SurveyResponse.survey_id == survey_data[
                                'event_id'],
                            SurveyResponse.row_id == survey_data['invite_id']
                        )).options(contains_eager(Survey.invited)).first()
                else:
                    c_abort(422, message='Token invalid', errors={
                        'token': ['Token invalid']})
            if model is None:
                c_abort(404, message='Survey id: %s does not exist' %
                                     str(row_id))
            result = SurveySchema(
                exclude=SurveySchema._default_exclude_fields).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class ReSendMailToSurveyInvitee(AuthResource):
    """
    Resend mail to all invitee which have not sent when survey launch
    """
    def put(self, row_id):
        """
        Call task for resend mail for particular survey
        :param row_id: id of survey
        :return:
        """
        # first find model
        model = None
        try:
            model = Survey.query.get(row_id)
            if model is None:
                c_abort(404, message='Survey id: %s'
                                     'does not exist' % str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            if model.editable :
                c_abort(422, message="Not editable")
            if model.is_in_process :
                c_abort(422, message="Already processing")

            send_survey_launch_email.s(True, row_id).delay()

            # true specifies mail sending task is in queue
            model.is_in_process = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Resent mail to Webinar id: %s' %
                           str(row_id)}, 200
