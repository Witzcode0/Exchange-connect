"""
API endpoints for "webinar invitees" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy import or_, and_
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.webinar_resources.webinar_invitees.models import WebinarInvitee
from app.webinar_resources.webinar_invitees.schemas import (
    WebinarInviteeSchema, WebinarInviteeReadArgsSchema)
from app.webinar_resources.webinars.models import Webinar
from app.webinar_resources.webinar_invitees.helpers import (
    register_webinar_conference_invitee, deregister_webinar_conference_invitee)
from app.webinar_resources.webinar_invitees import constants as WEBINARINVITEE
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT

from queueapp.webinars.stats_tasks import update_webinar_stats
from queueapp.webinars.email_tasks import send_webinar_register_email


class WebinarInviteeAPI(AuthResource):
    """
    CRUD API for managing webinar invitee
    """
    @swag_from('swagger_docs/webinar_invitees_post.yml')
    def post(self):
        """
        Create a webinar invitee
        """
        webinar_invitees_schema = WebinarInviteeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = webinar_invitees_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            webinar = Webinar.query.get(data.webinar_id)
            # only webinar creator can add invitee
            if webinar.created_by != g.current_user['row_id']:
                c_abort(403)
            # for cancelled webinar
            if webinar.cancelled:
                c_abort(422, errors='Webinar cancelled,'
                        ' so you cannot add invitees')
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            # update webinar stats
            update_webinar_stats.s(True, data.webinar_id).delay()
            # send an email to registered email(invitee email),
            # if webinar already launch
            if webinar.is_draft is False:
                send_webinar_register_email.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, invitee_id)=(345, 85) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id)=(3) is not present in table "webinar".
                # Key (invitee_id)=(134) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Webinar Invitee added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webinar_invitees_put.yml')
    def put(self, row_id):
        """
        Update a webinar invitee
        """
        webinar_invitees_schema = WebinarInviteeSchema()
        # first find model
        model = None
        try:
            model = WebinarInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar Invitee id: %s does '
                        'not exist' % str(row_id))
            # old_webinar_id, to be used for stats calculation
            wb_id = model.webinar_id
            webinar = Webinar.query.get(wb_id)
            # only webinar creator can update
            if webinar.created_by != g.current_user['row_id']:
                c_abort(403)
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
            data, errors = webinar_invitees_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(model.webinar_id)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        'so you cannot update invitees')
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            if wb_id != model.webinar_id:
                # update webinar stats
                update_webinar_stats.s(True, model.webinar_id).delay()
                update_webinar_stats.s(True, wb_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, invitee_id)=(345, 85) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id)=(3) is not present in table "webinar".
                # Key (invitee_id)=(134) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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
        return {'message': 'Updated Webinar Invitee id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/webinar_invitees_delete.yml')
    def delete(self, row_id):
        """
        Delete a webinar invitee
        """
        model = None
        invitee_id = None
        invitee_email = None
        try:
            # first find model
            model = WebinarInvitee.query.get(row_id)
            if model is None:
                c_abort(
                    404,
                    message='Webinar Invitee id: %s does not exist' %
                    str(row_id))
            # for bigmarker delete registration
            if model.invitee_id:
                invitee_id = model.invitee_id
            else:
                invitee_email = model.invitee_email
            # old_webinar_id, to be used for stats calculation
            wb_id = model.webinar_id
            # for cancelled webinar
            webinar = Webinar.query.get(wb_id)
            # ownership check
            if (not webinar.open_to_public and
                    model.created_by != g.current_user['row_id'] and
                    webinar.created_by != g.current_user['row_id']):
                c_abort(403)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        'so you cannot delete invitees')
            conference_id = webinar.conference_id
            db.session.delete(model)
            db.session.commit()
            # update webinar stats
            update_webinar_stats.s(True, wb_id).delay()
            if webinar.conference_id:
                response = deregister_webinar_conference_invitee(
                    model, conference_id=conference_id)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/webinar_invitees_get.yml')
    def get(self, row_id):
        """
        Get a webinar invitee by id
        """
        model = None
        try:
            # first find model
            model = WebinarInvitee.query.get(row_id)
            if model is None:
                c_abort(
                    404,
                    message='Webinar Inviteee id: %s does not exist' %
                    str(row_id))
            result = WebinarInviteeSchema(
                exclude=WebinarInviteeSchema._default_exclude_fields
            ).dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class WebinarInviteeListAPI(AuthResource):
    """
    Read API for webinar invitee lists, i.e, more than 1 project
    """
    model_class = WebinarInvitee

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['invitee', 'webinar']
        super(WebinarInviteeListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/webinar_invitees_get_list.yml')
    def get(self):
        """
        Get the list
        """
        webinar_invitees_read_schema = WebinarInviteeReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            webinar_invitees_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(WebinarInvitee), operator)
            # making a copy of the main output schema
            webinar_invitees_schema = WebinarInviteeSchema(
                exclude=WebinarInviteeSchema._default_exclude_fields)
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                webinar_invitees_schema = WebinarInviteeSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching webinar invitee types found')
            result = webinar_invitees_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class WebinarInviteeRegisterAPI(AuthResource):
    """
    API for webinar invitee registration and deregistration
    """
    @swag_from('swagger_docs/webinar_invitees_register_post.yml')
    def post(self):
        """
        Create a webinar invitee or change status(registered) for registration
        """
        webinar_invitees_schema = WebinarInviteeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            model = None
            open_to_account_types = []
            # validate and deserialize input into object
            data, errors = webinar_invitees_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(data.webinar_id)
            if webinar.cancelled:
                c_abort(422, errors='Webinar cancelled,'
                        ' so you cannot register')
            # check already invited user
            model = WebinarInvitee.query.filter(
                WebinarInvitee.webinar_id == data.webinar_id,
                or_(WebinarInvitee.invitee_id == g.current_user['row_id'],
                    WebinarInvitee.invitee_email == g.current_user[
                    'email'])).first()

            if model:
                data = model
                # change status to registered
                data.status = WEBINARINVITEE.REGISTERED
                data.updated_by = g.current_user['row_id']
            else:
                if webinar.open_to_account_types:
                    open_to_account_types = webinar.open_to_account_types
                if (not webinar.open_to_public and
                        not open_to_account_types or (
                        open_to_account_types and g.current_user[
                        'account_type'] not in open_to_account_types)):
                    c_abort(403)
                # link with user and invitee
                if not data.invitee_id:
                    user = User.query.filter(and_(
                        User.email == data.invitee_email,
                        User.account_type != ACCOUNT.ACCT_GUEST,
                        User.unverified.is_(False))).first()
                    if user:
                        data.invitee_id = user.row_id
                        data.invitee_email = None
                        data.invitee_first_name = None
                        data.invitee_last_name = None
                        data.invitee_designation = None
                        data.invitee_company = None
                # add new invitee
                data.status = WEBINARINVITEE.REGISTERED
                # no errors, so add data to db
                data.created_by = g.current_user['row_id']
                data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            if webinar.conference_id:
                response = register_webinar_conference_invitee(
                    invitee=data, conference_id=webinar.conference_id)
                if not response['status']:
                    if webinar.open_to_account_types:
                        db.session.delete(data)
                    else:
                        data.status = WEBINARINVITEE.INVITED
                    db.session.commit()
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'])
            # update webinar stats
            update_webinar_stats.s(True, data.webinar_id).delay()
            # send an email to new invitee email, if webinar already launch
            if not model and webinar.is_draft is False:
                send_webinar_register_email.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, invitee_id)=(345, 85) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id)=(3) is not present in table "webinar".
                # Key (invitee_id)=(134) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Webinar Invitee Registered: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/webinar_invitees_register_delete.yml')
    def delete(self, row_id):
        """
        Deregister webinar invitee
        """
        model = None
        invitee_id = None
        invitee_email = None
        try:
            # first find model
            model = WebinarInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Webinar Invitee id: %s does '
                        'not exist' % str(row_id))
            if (model.invitee_id != g.current_user['row_id'] and
                    model.invitee_email != g.current_user['email']):
                c_abort(403)
            # for bigmarker delete registration
            if model.invitee_id:
                invitee_id = model.invitee_id
            else:
                invitee_email = model.invitee_email
            # for cancelled webinar
            webinar = Webinar.query.get(model.webinar_id)
            if webinar.cancelled:
                c_abort(422, message='Webinar cancelled,'
                        ' so you cannot deregister')
            if webinar.conference_id:
                response = deregister_webinar_conference_invitee(
                    model, webinar.conference_id)
                if not response['status']:
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'])
            # change status to invited
            model.status = WEBINARINVITEE.INVITED
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
        return {'message': 'Webinar Invitee Deregistered: %s' %
                str(row_id), 'row_id': row_id}, 200


class PublicWebinarRegisterAPI(BaseResource):
    """
    API for public webinar invitee registration
    """

    def post(self):
        """
        Create a webinar invitee or change status(registered) for registration
        """
        webinar_invitees_schema = WebinarInviteeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = webinar_invitees_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled webinar
            webinar = Webinar.query.get(data.webinar_id)
            if not webinar:
                c_abort(404, message='Webinar id:'
                        '%s does not exist' % str(data.webinar_id))
            if webinar.cancelled:
                c_abort(422, errors='Webinar cancelled,'
                                    ' so you cannot register')
            if webinar.is_draft:
                c_abort(422, errors='Webinar not launch yet.')
            if not webinar.open_to_public:
                c_abort(403)
            # check already invited user
            model = WebinarInvitee.query.filter(
                WebinarInvitee.webinar_id == data.webinar_id,
                WebinarInvitee.status == WEBINARINVITEE.INVITED,
                and_(WebinarInvitee.invitee_id == data.invitee_id,
                     WebinarInvitee.invitee_email == data.invitee_email)
                ).first()

            if model:
                data = model
            # link with user and invitee
            if not data.invitee_id:
                user = User.query.filter(and_(
                    User.email == data.invitee_email,
                    User.account_type != ACCOUNT.ACCT_GUEST,
                    User.unverified.is_(False))).first()
                if user:
                    data.invitee_id = user.row_id
                    data.invitee_email = None
                    data.invitee_first_name = None
                    data.invitee_last_name = None
                    data.invitee_designation = None
                    data.invitee_company = None
            # add new invitee
            data.status = WEBINARINVITEE.REGISTERED
            # no errors, so add data to db
            data.created_by = webinar.created_by
            data.updated_by = webinar.created_by

            db.session.add(data)
            db.session.commit()
            if webinar.conference_id:
                response = register_webinar_conference_invitee(
                    invitee=data, conference_id=webinar.conference_id)
                if not response['status']:
                    db.session.delete(data)
                    db.session.commit()
                    c_abort(422, message='problem with bigmarker',
                            errors=response['response'])
            # update webinar stats
            update_webinar_stats.s(True, data.webinar_id).delay()
            # send an email to new invitee email, if webinar already launch
            if webinar.is_draft is False:
                send_webinar_register_email.s(True, data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id, invitee_email)=(193, tes@gmail.com)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (webinar_id)=(25) is not present in table "webinar".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
                c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
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

        return {'message': 'Webinar Invitee Registered: %s' %
                str(data.row_id), 'row_id': data.row_id,
                'conference_url': response['conference_url']}, 201
