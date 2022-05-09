"""
API endpoints for "unsubscriptions" package.
"""

import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from flask_restful import abort

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.resources.unsubscriptions.models import (Unsubscription,
    UnsubscribeReason)
from app.resources.unsubscriptions.schemas import (UnsubscriptionSchema,
     UnsubscribeReasonSchema, UnsubscribeReasonReadArgsSchema)
from app.resources.unsubscriptions.helpers import (
    verify_unsubscribe_email_token)


class UnsubscriptionAPI(BaseResource):
    """
    CRUD API for managing unsubscription
    """

    def post(self, token):
        """
        Create unsubcription
        """
        unsubscribe_schema = UnsubscriptionSchema()
        try:
            email = verify_unsubscribe_email_token(token)
            if not email:
                return c_abort(404, message='Bad email')

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
            model = Unsubscription.query.filter_by(email=email).first()
            data, errors = unsubscribe_schema.load(json_data, instance=model)
            if errors:
                c_abort(422, errors=errors)

            data.email = email
            data.modified_date = datetime.datetime.utcnow()
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


class UserUnsubscriptionAPI(AuthResource):

    def post(self):
        """
        Create unsubcription of current user
        """
        unsubscribe_schema = UnsubscriptionSchema()
        try:
            model = Unsubscription.query.filter_by(
                email=g.current_user['email']).first()

        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        try:
            data, errors = unsubscribe_schema.load(json_data, instance=model)
            if errors:
                c_abort(422, errors=errors)

            data.email = g.current_user['email']
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

        return {'message': 'Unsubcription Added'}, 201

    def put(self):
        """
        Update unsubcription of current user
        """
        unsubscribe_schema = UnsubscriptionSchema()
        try:
            model = Unsubscription.query.filter_by(
                email=g.current_user['email']).first()
            if not model:
                c_abort(404, message="Unsubscription doesn't exists "
                                     "for your email")

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
            data, errors = unsubscribe_schema.load(
                json_data, instance=model, partial=True)
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

        return {'message': 'Unsubcription Updated'}, 200

    def get(self):
        """
        Get unsubsription of current user
        """
        unsubscribe_schema = UnsubscriptionSchema()
        model = None
        try:
            # first find model
            model = Unsubscription.query.filter_by(
                email=g.current_user['email']).first()
            if not model:
                c_abort(404, message="Unsubscription doesn't exists "
                                     "for your email")
            result = unsubscribe_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    def delete(self):
        """
        Delete unsubsription of current user
        """
        model = None
        try:
            # first find model
            model = Unsubscription.query.filter_by(
                email=g.current_user['email']).first()
            if model is None:
                c_abort(404, message="Unsubscription doesn't exists "
                                     "for your email")

            db.session.delete(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204


class UnsubscribeReasonListAPI(BaseResource):
    """
    Read API for Unsubscriber reasons.
    """

    model_class = UnsubscribeReason

    def __init__(self, *args, **kwargs):
        super(UnsubscribeReasonListAPI, self).__init__(*args, **kwargs)

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

        return query, db_projection, s_projection, order, paging

    # @swag_from('swagger_docs/crm_contact_get_list.yml')
    def get(self):
        """
        Get the list
        """
        unsubscription_read_schema = \
            UnsubscribeReasonReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            unsubscription_read_schema)

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UnsubscribeReason), operator)
            # making a copy of the main output schema
            unsubscribe_reason_schema = UnsubscribeReasonSchema()
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching contact found')
            result = unsubscribe_reason_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
