"""
API endpoints for "crm contact note" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.crm_resources.crm_contact_notes.models import (
    CRMContactNote, crmusernotes)
from app.crm_resources.crm_contact_notes.schemas import (
    CRMContactNoteSchema, CRMContactNoteReadArgsSchema)
from app.crm_resources.crm_contact_notes.helpers import (
    build_query_for_related_user_notes)


class CRMContactNoteAPI(AuthResource):
    """
    CRUD API for managing crm contact note
    """

    def post(self):
        """
        Create a crm contact_note
        """

        crm_contact_note_schema = CRMContactNoteSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = crm_contact_note_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            db.session.add(data)
            db.session.commit()
            # manage user list
            if crm_contact_note_schema._cached_users:
                for cu in crm_contact_note_schema._cached_users:
                    if cu not in data.users:
                        data.users.append(cu)
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Note created: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update a crm contact note
        """

        crm_contact_note_schema = CRMContactNoteSchema()
        model = None

        try:
            model = CRMContactNote.query.get(row_id)
            if not model:
                c_abort(404, message='Note id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
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
            data, errors = crm_contact_note_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            db.session.add(data)
            db.session.commit()

            if (crm_contact_note_schema._cached_users or
                    'user_ids' in json_data):
                # add new ones
                for cu in crm_contact_note_schema._cached_users:
                    if cu not in data.users:
                        data.users.append(cu)
                # remove old ones
                for oldcu in data.users[:]:
                    if oldcu not in crm_contact_note_schema._cached_users:
                        data.users.remove(oldcu)
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

        return {'message': 'Updated contact note id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a contact note
        """

        model = None
        try:
            # first find model
            model = CRMContactNote.query.get(row_id)
            if model is None:
                c_abort(404, message='Note id: %s does not exist' %
                                     str(row_id))
            # check account membership and check user role
            if model.created_by != g.current_user['row_id']:
                c_abort(403)

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

    def get(self, row_id):
        """
        Get a contact note by id
        """

        crm_contact_note_schema = CRMContactNoteSchema()

        model = None
        try:
            model = CRMContactNote.query.get(row_id)
            if model is None:
                c_abort(404, message='Note id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                c_abort(403)
            result = crm_contact_note_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CRMContactNoteListAPI(AuthResource):
    """
    Read API for CRM contact note lists, i.e, more than 1 contact note
    """
    model_class = CRMContactNote

    def __init__(self, *args, **kwargs):
        super(CRMContactNoteListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        user_id = None
        if 'user_id' in filters and filters['user_id']:
            user_id = filters.pop('user_id')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        # build specific extra queries filters
        if extra_query:
            pass
        # for own created note
        query_filters['base'].append(
            CRMContactNote.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.options(joinedload(CRMContactNote.account))
        if user_id:
            query = query.join(
                crmusernotes, crmusernotes.c.note_id ==
                CRMContactNote.row_id).filter(
                crmusernotes.c.user_id == user_id)
            # all event related note query
            event_query_creator = build_query_for_related_user_notes(
                created_by=g.current_user['row_id'], user_id=user_id,
                query_session=query_session)
            final_query = query.union(event_query_creator)
        else:
            final_query = query

        return final_query, db_projection, s_projection, order, paging

    # @swag_from('swagger_docs/crm_file_library_get_list.yml')
    def get(self):
        """
        Get the list
        """
        # schema for reading get arguments
        crm_contact_note_read_schema = CRMContactNoteReadArgsSchema(
            strict=True)

        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_contact_note_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CRMContactNote), operator)
            # making a copy of the main output schema
            crm_contact_note_schema = CRMContactNoteSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_contact_note_schema = CRMContactNoteSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching notes found')
            result = crm_contact_note_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
