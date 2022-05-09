"""
API endpoints for "corporate access event collaborators" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_collaborators.\
    schemas import (CorporateAccessEventCollaboratorSchema,
                    CorporateAccessEventCollaboratorReadArgsSchema)
from app.corporate_access_resources.corporate_access_events.models \
    import CorporateAccessEvent

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)


class CorporateAccessEventCollaboratorAPI(AuthResource):
    """
    CRUD API for managing corporate access event collaborators
    """

    @swag_from('swagger_docs/corporate_access_event_collaborators_post.yml')
    def post(self):
        """
        Create a corporate access event collaborators
        """
        corp_access_event_collaborator_schema = \
            CorporateAccessEventCollaboratorSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = corp_access_event_collaborator_schema.load(
                json_data)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(
                data.corporate_access_event_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot add collaborators')
            # no errors, so add data to db
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
                # Key (corporate_access_event_id, collaborator_id) = \
                # (3, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(10) is \
                # not present in table "corporate_access_event_collaborator".
                # Key (collaborator_id)=(4) is not present in table "user".
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

        return {'message': 'Corporate Access Event Collaborator added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_access_event_collaborators_put.yml')
    def put(self, row_id):
        """
        Update a corporate access event collaborator
        """
        corp_access_event_collaborator_schema = \
            CorporateAccessEventCollaboratorSchema()
        # first find model
        model = None
        try:
            model = CorporateAccessEventCollaborator.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event Collaborator '
                        'id: %s does not exist' % str(row_id))
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
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
            data, errors = corp_access_event_collaborator_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot update collaborators')
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
                # Key (corporate_access_event_id, collaborator_id)= \
                # (3, 3) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(10) is not \
                # present in table "corporate_access_event".
                # Key (collaborator_id)=(4) is not present in table "user".
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
        return {'message': 'Updated Corporate Access Event collaborator id: %s'
                           % str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_event_collaborators_delete.yml')
    def delete(self, row_id):
        """
        Delete a corporate access event collaborator
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEventCollaborator.query.get(row_id)
            if model is None:
                c_abort(
                    404, message='Corporate Access Event Collaborator id: %s'
                    ' does not exist' % str(row_id))
            # old_corporate_access_event_id, to be used for stats calculation
            ce_id = model.corporate_access_event_id
            # for cancelled cae
            cae = CorporateAccessEvent.query.get(ce_id)
            if cae.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        'so you cannot delete collaborators')
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

    @swag_from('swagger_docs/corporate_access_event_collaborators_get.yml')
    def get(self, row_id):
        """
        Get a corporate access event collaborator by id
        """
        corp_access_event_collaborator_schema = \
            CorporateAccessEventCollaboratorSchema()
        model = None
        try:
            # first find model
            model = CorporateAccessEventCollaborator.query.get(row_id)
            if model is None:
                c_abort(
                    404, message='Corporate Access Event Collaborator id: %s'
                    ' does not exist' % str(row_id))
            result = corp_access_event_collaborator_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventCollaboratorListAPI(AuthResource):
    """
    Read API for corporate access event collaborator list,
    i.e, more than 1 corporate access event collaborator
    """
    model_class = CorporateAccessEventCollaborator

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['corporate_access_event',
                                    'collaborator', 'creator']
        super(CorporateAccessEventCollaboratorListAPI, self).__init__(
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

    @swag_from(
        'swagger_docs/corporate_access_event_collaborators_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corp_access_event_collaborator_read_schema = \
            CorporateAccessEventCollaboratorReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corp_access_event_collaborator_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CorporateAccessEventCollaborator), operator)
            # making a copy of the main output schema
            corp_access_event_collaborator_schema = \
                CorporateAccessEventCollaboratorSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corp_access_event_collaborator_schema = \
                    CorporateAccessEventCollaboratorSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                        ' access event collaborators found')
            result = corp_access_event_collaborator_schema.dump(
                models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
