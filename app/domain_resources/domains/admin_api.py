"""
API endpoints for "admin domains" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.domain_resources.domains.models import Domain
from app.domain_resources.domains.schemas import (
    DomainSchema, DomainReadArgsSchema)
from app.domain_resources.domain_config.models import DomainConfig
from app.resources.roles import constants as ROLE
from app.resources.accounts.schemas import AccountSchema
from app.resources.accounts import constants as ACCT
from app.resources.account_settings.models import AccountSettings
from app.resources.account_stats.models import AccountStats
from app.resources.account_profiles.models import AccountProfile
from app.domain_resources.domains.helpers import get_domain_info


class DomainAPI(AuthResource):
    """
    Create, update, delete API for domains
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/domain_post.yml')
    def post(self):
        """
        Create an domain
        """
        domain_schema = DomainSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = domain_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            # inserting required config
            data.domain_configs = [DomainConfig(
                name='FRONTEND_DOMAIN', value=data.name)]
            db.session.add(data)
            db.session.commit()
            # creating guest user account for the domain
            account_detail = {
                "account_name": "default_guest_account_" + data.code ,
                "account_type": ACCT.ACCT_GUEST,
                "domain_id": data.row_id,
                "profile": {}
            }
            account, errors = AccountSchema().load(
                account_detail)
            if errors:
                db.session.delete(data)
                db.session.commit()
                c_abort(422, errors=errors)
            account.created_by = 1
            account.updated_by = 1
            account.stats = AccountStats()
            account.settings = AccountSettings()
            account.profile = AccountProfile()
            account.profile.account_type = ACCT.ACCT_GUEST
            db.session.add(account)
            db.session.commit()
            get_domain_info.cache_clear()

        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.exception(e)
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (lower(domain_name::text))=(abc) already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Domain added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/domain_put.yml')
    def put(self, row_id):
        """
        Update an domain
        """
        domain_schema = DomainSchema()
        # first find model
        model = None
        try:
            model = Domain.query.get(row_id)
            if model is None:
                c_abort(404, message='Domain id: %s'
                        ' does not exist' % str(row_id))
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
            data, errors = domain_schema.load(
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
                # Key (lower(domain_name::text))=(abc) already exists.
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
        return {'message': 'Updated Domain id: %s' %
                str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/domain_delete.yml')
    def delete(self, row_id):
        """
        Delete an domain
        """
        try:
            # first find model
            model = Domain.query.get(row_id)
            if model is None:
                c_abort(404, message='Domain id: %s'
                        ' does not exist' % str(row_id))

            db.session.delete(model)
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

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/domain_get.yml')
    def get(self, row_id):
        """
        Get an domain by id
        """
        model = None
        try:
            # first find model
            model = Domain.query.get(row_id)
            if model is None:
                c_abort(404, message='Domain id: %s'
                        ' does not exist' % str(row_id))
            result = DomainSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data}, 200


class DomainListAPI(BaseResource):
    """
    Read API for domain lists, i.e, more than 1 domain
    """
    model_class = Domain

    def __init__(self, *args, **kwargs):
        super(DomainListAPI, self).__init__(*args, **kwargs)

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
        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/domain_get_list.yml')
    def get(self):
        """
        Get the list
        """
        domain_read_schema = DomainReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            domain_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Domain), operator)
            # making a copy of the main output schema
            domain_schema = DomainSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                domain_schema = DomainSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching domains found')
            result = domain_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200

