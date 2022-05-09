"""
ADMIN API endpoints for "unsubscriptions" package.
"""


from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.unsubscriptions.models import (
    Unsubscription, UnsubscribeReason)
from app.resources.unsubscriptions.schemas import (
    UnsubscriptionSchema, UnsubscriptionReadArgsSchema,
    UnsubscribeReasonSchema)
from app.resources.roles import constants as ROLE


class AdminUnsubscriptionAPI(AuthResource):

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def put(self, row_id):
        """
        Update unsubcription
        """
        unsubscribe_schema = UnsubscriptionSchema()
        try:
            model = Unsubscription.query.get(row_id)
            if not model:
                c_abort(404, message='Unsubscription id: '
                        '%s does not exist' % str(row_id))

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            json_data = {}
        try:
            data, errors = unsubscribe_schema.load(json_data, instance=model)
            if errors:
                c_abort(422, errors=errors)
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (email)=(example@example.com) already exists.
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

        return {'message': 'Unsubcription Updated: %s' % str(row_id),
                'row_id': row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def get(self, row_id):
        """
        Get an unsubsription by id
        """
        unsubscribe_schema = UnsubscriptionSchema()
        model = None
        try:
            # first find model
            model = Unsubscription.query.get(row_id)
            if not model:
                c_abort(404, message='Unsubscription id:%s does not exist'
                                     % str(row_id))
            result = unsubscribe_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def delete(self, row_id):
        """
        Delete a unsubsription
        """
        model = None
        try:
            # first find model
            model = Unsubscription.query.get(row_id)
            if model is None:
                c_abort(404, message='Unsubsription id: %s does not exist' %
                                     str(row_id))
            if (g.current_user['email'] != model.email and
                    ROLE.EPT_AA not in g.current_user['role']['permissions']):
                c_abort(403)

            db.session.delete(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204


class UnsubscriptionListAPI(AuthResource):
    """
    Read API for  Admin to get list of Unsubscribers
    """

    model_class = Unsubscription

    def __init__(self, *args, **kwargs):
        super(UnsubscriptionListAPI, self).__init__(*args, **kwargs)

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

        if extra_query:
            pass

        query = self._build_final_query(query_filters, query_session, operator)
        query = query.filter(Unsubscription.events != '{}')

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    # @swag_from('swagger_docs/crm_contact_get_list.yml')
    def get(self):
        """
        Get the list
        """
        unsubscription_read_schema = UnsubscriptionReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            unsubscription_read_schema)

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Unsubscription), operator)
            # making a copy of the main output schema
            unsubscribe_schema = UnsubscriptionSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                unsubscribe_schema = UnsubscriptionSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching contact found')
            result = unsubscribe_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class UnsubscribeReasonAPI(AuthResource):

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def post(self):
        """
        create unsubscribe reason
        """
        unsubscribe_reason_schema = UnsubscribeReasonSchema()
        json_data = request.get_json()

        if not json_data:
            c_abort(422, message="no data received.")

        try:

            data, errors = unsubscribe_reason_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (email)=(example@example.com) already exists.
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

        return {'message': 'Unsubcription Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def put(self, row_id):
        """
        Update unsubcribe reason
        """
        unsubscribe_reason_schema = UnsubscribeReasonSchema()

        model = UnsubscribeReason.query.get(row_id)
        if not model:
            c_abort(404, message='Unsubscribe reason id: '
                    '%s does not exist' % str(row_id))

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(422, message="no data received.")
        try:
            data, errors = unsubscribe_reason_schema.load(
                json_data, instance=model)
            if errors:
                c_abort(422, errors=errors)
            db.session.add(data)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (email)=(example@example.com) already exists.
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

        return {'message': 'Unsubcription Updated: %s' % str(row_id),
                'row_id': row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    def get(self, row_id):
        """
        Get an unsubsribe reason by id
        """
        result = []
        unsubscribe_reason_schema = UnsubscribeReasonSchema()
        try:
            # first find model
            model = UnsubscribeReason.query.get(row_id)
            if not model:
                c_abort(404, message='Unsubscribe reason id: %s does not exist'
                                     % str(row_id))
            result = unsubscribe_reason_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200
