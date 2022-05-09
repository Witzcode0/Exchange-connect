"""
API endpoints for "crm distribution list" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.exc import IntegrityError
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList
from app.crm_resources.crm_distribution_invitee_lists.models import (
    CRMDistributionInviteeList)
from app.crm_resources.crm_distribution_invitee_lists.schemas import (
    CRMDistributionInviteeListSchema, CRMDistributionInviteeListReadArgsSchema)

from queueapp.crm_distribution_lists.email_tasks import (
    send_distribution_invitee_list_email)


class CRMDistributionInviteeAPI(AuthResource):
    """
    For creating new crm distribution invitee list
    """

    def post(self):
        """
        Create crm distribution list
        :return:
        """

        crm_distribution_invitee_schema = CRMDistributionInviteeListSchema()

        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = crm_distribution_invitee_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            distribution_data = CRMDistributionList.query.filter(
                CRMDistributionList.row_id == data.distribution_list_id).first()
            # check ownership
            if distribution_data.created_by != g.current_user['row_id']:
                c_abort(403)
            data.created_by = g.current_user['row_id']
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            if not distribution_data.is_draft:
                send_distribution_invitee_list_email.s(
                    True, distribution_data.row_id).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id, participant_email)=(
                # 193, tes@gmail.com) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            elif APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (distribution_list_id)=(25) is not present
                # in table "crm_distribution_invitee_list".
                column = e.orig.diag.message_detail.split('(')[1].split(')')[0]
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

        return {'message': 'Distribution Invitee List created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201


class CRMDistributionInviteeListAPI(AuthResource):
    """
    Read API for Corporate Access Event lists, i.e, more than 1
    """
    model_class = CRMDistributionInviteeList

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = []
        super(CRMDistributionInviteeListAPI, self).__init__(*args, **kwargs)

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

        query_filters['base'].append(
            CRMDistributionInviteeList.created_by == g.current_user['row_id'])

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """

        models = []
        total = 0
        crm_distribution_Invitee_read_schema = \
            CRMDistributionInviteeListReadArgsSchema(strict=True)
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_distribution_Invitee_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CRMDistributionList),
                                 operator)
            crm_distr_invitee_schema = CRMDistributionInviteeListSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_distr_invitee_schema = CRMDistributionInviteeListSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching distribution list found')
            result = crm_distr_invitee_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
