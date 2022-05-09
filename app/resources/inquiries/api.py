"""
API endpoints for "inquiry" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.auth.decorators import role_permission_required
from app.base.api import BaseResource, AuthResource
from app.resources.inquiries.models import Inquiry
from app.resources.inquiries.schemas import (
    InquirySchema, InquiryReadArgsSchema, InquiryContactUsSchema,
    InquiryPlanSchema)
from app.resources.roles import constants as ROLE
from app.domain_resources.domains.helpers import (
    get_domain_name, get_domain_info)

from queueapp.inquiry_tasks import (
    send_inquiry_contact_us_email, send_inquiry_plan_email)


class InquiryContactUsPostAPI(BaseResource):
    """
    Post API for contact us inquiries
    """

    @swag_from('swagger_docs/inquiry_contact_us_post.yml')
    def post(self):
        """
        Create a inquiry
        """
        inquiry_contact_us_schema = InquiryContactUsSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = inquiry_contact_us_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            domain_id, domain_config = get_domain_info(get_domain_name())
            data.domain_id = domain_id
            db.session.add(data)
            db.session.commit()
            send_inquiry_contact_us_email.s(True, data.row_id).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Inquiry added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201


class InquiryPlanPostAPI(AuthResource):
    """
    Post API for plan inquiries
    """

    @swag_from('swagger_docs/inquiry_plan_post.yml')
    def post(self):
        """
        Create a inquiry
        """
        inquiry_plan_schema = InquiryPlanSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = inquiry_plan_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.name = g.current_user['profile']['first_name']
            data.email = g.current_user['email']
            data.contact_number = g.current_user['profile']['phone_number']
            # no errors, so add data to db
            domain_id, domain_config = get_domain_info(get_domain_name())
            data.domain_id = domain_id
            db.session.add(data)
            db.session.commit()
            send_inquiry_plan_email.s(True, data.row_id).delay()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Inquiry added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201


class InquiryAPI(AuthResource):
    """
    Get and put API for managing inquiries by super-admin
    """
    @role_permission_required(perms=[ROLE.EPT_AA])
    @swag_from('swagger_docs/inquiry_put.yml')
    def put(self, row_id):
        """
        Update a inquiry
        """
        inquiry_schema = InquirySchema()
        # first find model
        model = None
        try:
            model = Inquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='Inquiry id: %s does'
                        ' not exist' % str(row_id))
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
            data, errors = inquiry_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            data.updated_by = g.current_user['row_id']
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Updated Inquiry id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA])
    @swag_from('swagger_docs/inquiry_get.yml')
    def get(self, row_id):
        """
        Get inquiry by id
        """
        inquiry_schema = InquirySchema()
        model = None
        try:
            # first find model
            model = Inquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='Inquiry id: %s does'
                        ' not exist' % str(row_id))
            result = inquiry_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class InquiryListAPI(AuthResource):
    """
    Read API for inquiry lists, i.e, more than 1 inquiry
    """
    model_class = Inquiry

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['editor', 'creator', 'account']
        super(InquiryListAPI, self).__init__(*args, **kwargs)

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

    @role_permission_required(perms=[ROLE.EPT_AA])
    @swag_from('swagger_docs/inquiry_get_list.yml')
    def get(self):
        """
        Get the list
        """
        inquiry_read_schema = InquiryReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            inquiry_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Inquiry), operator)
            # making a copy of the main output schema
            inquiry_schema = InquirySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                inquiry_schema = InquirySchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching inquiries found')
            result = inquiry_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
