"""
API endpoints for "Disclosure enhancement peer group" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base import constants as APP
from app.base.api import AuthResource
from app.disclosure_enhancement_resources.de_peer_groups.models import (
    DePeerGroup)
from app.disclosure_enhancement_resources.de_peer_groups.schemas import (
    DePeerGroupSchema, DePeerGroupReadArgsSchema)


class DePeerGroupAPI(AuthResource):
    """
    CRUD API for managing Disclosure enhancement peer group
    """
    @swag_from('swagger_docs/de_peer_groups_post.yml')
    def post(self):
        """
        Create a Disclosure enhancement peer group
        """
        de_peer_group_schema = DePeerGroupSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = de_peer_group_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by

            db.session.add(data)
            db.session.commit()

            # manage companies list
            if de_peer_group_schema._cached_ids:
                for cid in de_peer_group_schema._cached_ids:
                    if cid not in data.companies:
                        data.companies.append(cid)
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (company_id)=(1) is not present in table "company"
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

        return {'message': 'Disclosure enhancement peer group added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/de_peer_groups_put.yml')
    def put(self, row_id):
        """
        Update Disclosure enhancement peer group by id
        """
        de_peer_group_schema = DePeerGroupSchema()
        model = None
        try:
            model = DePeerGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Disclosure enhancement peer group id: %s'
                        ' does not exist' % str(row_id))
            # only current user can change  peer group
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
            data, errors = de_peer_group_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            if de_peer_group_schema._cached_ids or 'company_ids' in json_data:
                # add new ones
                for cid in de_peer_group_schema._cached_ids:
                    if cid not in data.companies:
                        data.companies.append(cid)
                # remove old ones
                for oldcid in data.companies[:]:
                    if oldcid not in de_peer_group_schema._cached_ids:
                        data.companies.remove(oldcid)
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Forbidden as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Peer Group id: %s' % str(row_id)}, 200

    @swag_from('swagger_docs/de_peer_groups_delete.yml')
    def delete(self, row_id):
        """
        Delete Disclosure enhancement peer group by id
        """
        model = None
        try:
            model = DePeerGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Disclosure enhancement peer group id: %s'
                        ' does not exist' % str(row_id))
            if model.created_by != g.current_user['row_id']:
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

    @swag_from('swagger_docs/de_peer_groups_get.yml')
    def get(self, row_id):
        """
        Get a Disclosure enhancement peer group by id
        """
        de_peer_group_schema = DePeerGroupSchema()
        model = None
        try:
            # first find model
            model = DePeerGroup.query.get(row_id)
            if model is None:
                c_abort(404, message='Disclosure enhancement peer group id: %s'
                        ' does not exist' % str(row_id))
            result = de_peer_group_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class DePeerGroupListAPI(AuthResource):
    """
    Read API for Disclosure enhancement peer group lists, i.e,
    more than 1 peergroup
    """

    model_class = DePeerGroup

    def __init__(self, *args, **kwargs):
        super(DePeerGroupListAPI, self).__init__(*args, **kwargs)

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

    @swag_from('swagger_docs/de_peer_groups_get_list.yml')
    def get(self):
        """
        Get the list
        """
        de_peer_group_read_schema = DePeerGroupReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            de_peer_group_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(DePeerGroup), operator)
            # making a copy of the main output schema
            de_peer_group_schema = DePeerGroupSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                de_peer_group_schema = DePeerGroupSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Disclosure enhancement '
                        'peer groups found')
            result = de_peer_group_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
