"""
API endpoints for "corporate access event invitees" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy import and_, or_
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_invitees.schemas \
    import (
        CorporateAccessEventInviteeSchema,
        CorporateAccessEventInviteeReadArgsSchema,
        CAOneToOneEventInviteeSchema)
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_invitees import (
    constants as CORPORATEACCESSEVENTINVITEE)
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT
from app.resources.notifications import constants as NOTIFY

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)
from queueapp.corporate_accesses.email_tasks import (
    send_corporate_access_event_register_email)
from queueapp.corporate_accesses.notification_tasks import (
    add_cae_invitee_joined_rejected_notification)


class CorporateAccessEventInviteeAPI(AuthResource):
    """
    CRUD API for managing Corporate Access Event invitee
    """
    @swag_from('swagger_docs/corporate_access_event_invitees_post.yml')
    def post(self):
        """
        Create a Corporate Access Event invitee
        """
        corporate_invitees_schema = CorporateAccessEventInviteeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            collaborator_ids = []
            data, errors = corporate_invitees_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            event_data = CorporateAccessEvent.query.get(
                data.corporate_access_event_id)
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            if (event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in collaborator_ids and
                    event_data.event_type.is_meeting):
                c_abort(403)
            # for cancelled event
            if event_data.cancelled:
                c_abort(422, errors='Corporate Access Event cancelled,'
                        ' so you cannot add an invitee')
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            update_corporate_event_stats.s(
                True, data.corporate_access_event_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (created_by, corporate_access_event_id, invitee_id,
                # invitee_email)=(12, 1, 13, s@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present
                # in table "corporate_access_event".
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

        return {'message': 'Corporate Access Event Invitee added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_access_event_invitees_put.yml')
    def put(self, row_id):
        """
        Update a Corporate Access Event invitee
        """
        corporate_invitees_schema = CorporateAccessEventInviteeSchema()
        # first find model
        model = None
        try:
            model = CorporateAccessEventInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'Invitee id: %s does not exist' % str(row_id))
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
            event_data = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            collaborator_ids = [col.collaborator_id
                                for col in event_data.collaborators]
            # only collaborators and creator can change invitee
            if (event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in collaborator_ids and
                    model.created_by != g.current_user['row_id']):
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
            data, errors = corporate_invitees_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled event
            event = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            if event.cancelled:
                c_abort(422, errors='Corporate Access Event cancelled,'
                        ' so you cannot update an invitee')
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # old_corporate_access_event_id, to be used for stats calculation
            if ce_id != model.corporate_access_event_id:
                update_corporate_event_stats.s(
                    True, model.corporate_access_event_id).delay()
                update_corporate_event_stats.s(True, ce_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (created_by, corporate_access_event_id, invitee_id,
                # invitee_email)=(12, 1, 13, s@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present
                # in table "corporate_access_event".
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
        return {'message': 'Updated Corporate Access Event Invitee id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_event_invitees_delete.yml')
    def delete(self, row_id):
        """
        Delete a Corporate Access Event invitee
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEventInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'Invitee id: %s does not exist' % str(row_id))
            # for cancelled event
            event = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            if event.cancelled:
                c_abort(422, errors='Corporate Access Event cancelled,'
                        ' so you cannot delete an inquiry')
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
            db.session.delete(model)
            db.session.commit()
            # old_corporate_access_event_id, to be used for stats calculation
            update_corporate_event_stats.s(True, ce_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/corporate_access_event_invitees_get.yml')
    def get(self, row_id):
        """
        Get a Corporate Access Event invitee by id
        """
        corporate_invitees_schema = CorporateAccessEventInviteeSchema()
        model = None
        try:
            # first find model
            model = CorporateAccessEventInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'Invitee id: %s does not exist' % str(row_id))
            result = corporate_invitees_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventInviteeListAPI(AuthResource):
    """
    Read API for corporate access event invitee lists, i.e, more than 1
    """
    model_class = CorporateAccessEventInvitee

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['invitee', 'corporate_access_event']
        super(CorporateAccessEventInviteeListAPI, self).__init__(
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
        # build specific extra queries filters
        if extra_query:
            pass

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_access_event_invitees_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corporate_invitees_read_schema = \
            CorporateAccessEventInviteeReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_invitees_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CorporateAccessEventInvitee), operator)
            # making a copy of the main output schema
            corporate_invitees_schema = CorporateAccessEventInviteeSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corporate_invitees_schema = CorporateAccessEventInviteeSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(
                    404, message='No matching corporate access '
                    'invitee types found')
            result = corporate_invitees_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class CorporateAccessEventInviteeJoinedAPI(AuthResource):
    """
    Put api for managing Corporate Access Event invitee join
    """

    @swag_from('swagger_docs/corporate_access_event_invitee_joined.yml')
    def put(self, row_id):
        """
        Change status of event invitee
        """
        model = None
        event_data = None
        try:
            # first find model
            model = CorporateAccessEventInvitee.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                                     'Invitee id: %s does not exist' %
                                     str(row_id))
            # only invitee can joined particular event
            if (model.user_id != g.current_user['row_id'] or
                    (g.current_user['account_type'] == ACCOUNT.ACCT_GUEST and
                        model.invitee_email != g.current_user['email'])):
                c_abort(403)

            event_data = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            if not event_data:
                c_abort(404, message='Corporate Access Event '
                                     'id: %s does not exist' %
                                     str(event_data.row_id))
            # if has_slots true so no authority to join event
            if event_data.event_sub_type.has_slots:
                c_abort(403)

            model.status = CORPORATEACCESSEVENTINVITEE.JOINED
            db.session.add(model)
            db.session.commit()
            update_corporate_event_stats.s(
                True, model.corporate_access_event_id).delay()
            add_cae_invitee_joined_rejected_notification.s(
                True, model.row_id,
                NOTIFY.NT_COR_EVENT_INVITED_ACCEPTED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (created_by, corporate_access_event_id, invitee_id,
                # invitee_email)=(12, 1, 13, s@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present
                # in table "corporate_access_event".
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

        return {'message': 'Joined Corporate Access Event Invitee id: %s' %
                           str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_event_invitee_unjoined.yml')
    def delete(self, row_id):
        """
        Unjoined invitee by invited user
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEventInvitee.query.filter(and_(
                CorporateAccessEventInvitee.row_id == row_id,
                or_(CorporateAccessEventInvitee.status ==
                    CORPORATEACCESSEVENTINVITEE.JOINED,
                    CorporateAccessEventInvitee.status ==
                    CORPORATEACCESSEVENTINVITEE.INVITED))).first()
            if model is None:
                c_abort(404, message='Corporate Access Event '
                                     'Invitee id: %s does not exist' %
                                     str(row_id))
            # only invitee can un-joined invitee
            if (model.user_id != g.current_user['row_id'] or
                    (g.current_user['account_type'] == ACCOUNT.ACCT_GUEST and
                        model.invitee_email != g.current_user['email'])):
                c_abort(403)
            # if meeting type event so invitee can change
            # the status as rejected
            ca_event_id = model.corporate_access_event_id
            if model.corporate_access_event.event_type.is_meeting:
                invitee_schema = CAOneToOneEventInviteeSchema()
                json_data = request.get_json()
                if json_data:
                    data, errors = invitee_schema.load(json_data)
                    if errors:
                        c_abort(422, errors=errors)

                    if 'invitee_remark' in data and data['invitee_remark']:
                        model.invitee_remark = data['invitee_remark']
                model.status = CORPORATEACCESSEVENTINVITEE.REJECTED
            else:
                model.status = CORPORATEACCESSEVENTINVITEE.INVITED

            if model.corporate_access_event.open_to_all and model.uninvited:
                db.session.delete(model)
                model = None
            else:
                db.session.add(model)
            db.session.commit()
            update_corporate_event_stats.s(True, ca_event_id).delay()
            if model and model.status == CORPORATEACCESSEVENTINVITEE.REJECTED:
                add_cae_invitee_joined_rejected_notification.s(
                    True, model.row_id,
                    NOTIFY.NT_COR_EVENT_INVITED_REJECTED).delay()

        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Unjoined Corporate Access Event Invitee id: %s' %
                str(row_id)}, 204


class CorporateAccessEventInviteeRegisterAPI(AuthResource):
    """
    API for corporate access invitee registration and deregistration
    """

    def post(self):
        """
        Create a corporate access invitee or change status(registered)
        for registration
        """
        ca_invitees_schema = CorporateAccessEventInviteeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            model = None
            # validate and deserialize input into object
            if 'invitee_id' in json_data and json_data['invitee_id']:
                json_data['invitee_id'] = g.current_user['row_id']

            data, errors = ca_invitees_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # for cancelled webinar
            ca_event = CorporateAccessEvent.query.get(
                data.corporate_access_event_id)
            if ca_event.cancelled:
                c_abort(422, errors='CAEvent cancelled,'
                        ' so you cannot register')
            if ca_event.is_draft:
                c_abort(422, errors='CAEvent not launch yet.')

            if (ca_event.open_to_all and
                    g.current_user['account_type'] not in
                    ca_event.account_type_preference):
                c_abort(403)
            # check already invited user
            model = CorporateAccessEventInvitee.query.filter(
                CorporateAccessEventInvitee.corporate_access_event_id ==
                data.corporate_access_event_id,
                or_(CorporateAccessEventInvitee.invitee_id ==
                    g.current_user['row_id'],
                    CorporateAccessEventInvitee.invitee_email ==
                    g.current_user['email'])).first()

            if model:
                data = model
            else:
                if not ca_event.event_sub_type.has_slots:
                    data.status = CORPORATEACCESSEVENTINVITEE.JOINED
                else:
                    data.status = CORPORATEACCESSEVENTINVITEE.INVITED
                # link with user and invitee
                if not data.invitee_id:
                    user = User.query.filter(and_(
                        User.email == data.invitee_email,
                        User.account_type != ACCOUNT.ACCT_GUEST,
                        User.unverified.is_(False))).first()
                    if user:
                        data.invitee_id = user.row_id
                        data.user_id = user.row_id
                        data.invitee_email = None
                        data.invitee_first_name = None
                        data.invitee_last_name = None
                        data.invitee_designation = None
                else:
                    data.user_id = data.invitee_id
                # no errors, so add data to db
                data.uninvited = True
                data.created_by = g.current_user['row_id']
                data.updated_by = data.created_by
                db.session.add(data)
                db.session.commit()
                # update ca_event stats
                update_corporate_event_stats.s(
                    True, data.corporate_access_event_id).delay()
                # send an email to new invitee email,
                # if ca event already launch
                send_corporate_access_event_register_email.s(
                    True, data.corporate_access_event_id, data.row_id).delay()
                add_cae_invitee_joined_rejected_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_INVITED_ACCEPTED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, invitee_id)=(345, 85)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present in
                # table "corporate_access_event".
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

        return {'message': 'Corporate access event Invitee Registered: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201


class CorporateAccessEventNoAuthInviteeRegisterAPI(BaseResource):
    """
    API for corporate access invitee registration and deregistration
    """

    def post(self):
        """
        Create a corporate access invitee or change status(registered)
        for registration
        """
        ca_invitees_schema = CorporateAccessEventInviteeSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            model = None
            # validate and deserialize input into object
            data, errors = ca_invitees_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # for cancelled webinar
            ca_event = CorporateAccessEvent.query.get(
                data.corporate_access_event_id)
            if ca_event.cancelled:
                c_abort(422, errors='CAEvent cancelled,'
                        ' so you cannot register')
            if ca_event.is_draft:
                c_abort(422, errors='CAEvent not launch yet.')

            if not ca_event.open_to_all:
                c_abort(403)
            # check already invited user
            model = CorporateAccessEventInvitee.query.filter(
                CorporateAccessEventInvitee.corporate_access_event_id ==
                data.corporate_access_event_id,
                CorporateAccessEventInvitee.invitee_email ==
                data.invitee_email).first()

            if model:
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    'invitee_email': [APP.MSG_ALREADY_EXISTS]})
            else:
                if not ca_event.event_sub_type.has_slots:
                    data.status = CORPORATEACCESSEVENTINVITEE.JOINED
                else:
                    data.status = CORPORATEACCESSEVENTINVITEE.INVITED
                # link with user and invitee
                if not data.invitee_id:
                    user = User.query.filter(and_(
                        User.email == data.invitee_email,
                        User.account_type != ACCOUNT.ACCT_GUEST,
                        User.unverified.is_(False))).first()
                    if user:
                        data.invitee_id = user.row_id
                        data.user_id = user.row_id
                        data.invitee_email = None
                        data.invitee_first_name = None
                        data.invitee_last_name = None
                        data.invitee_designation = None
                        data.invitee_company = None
                else:
                    data.user_id = data.invitee_id
                # no errors, so add data to db
                data.uninvited = True
                data.created_by = ca_event.created_by
                data.updated_by = data.created_by
                db.session.add(data)
                db.session.commit()
                # update ca_event stats
                update_corporate_event_stats.s(
                    True, data.corporate_access_event_id).delay()
                # send an email to new invitee email,
                # if ca event already launch
                send_corporate_access_event_register_email.s(
                    True, data.corporate_access_event_id, data.row_id).delay()
                add_cae_invitee_joined_rejected_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_COR_EVENT_INVITED_ACCEPTED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, invitee_id)=(345, 85)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present in
                # table "corporate_access_event".
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

        return {'message': 'Corporate access event Invitee Registered: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201
