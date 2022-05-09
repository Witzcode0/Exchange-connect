"""
API endpoints for "event file library" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from flasgger.utils import swag_from

from app import db, c_abort, eventfile
from app.base.api import AuthResource
from app.base import constants as APP
from app.common.helpers import (
    store_file, delete_files, file_type_for_thumbnail, delete_fs_file)
from app.resources.event_file_library.models import EventLibraryFile
from app.resources.event_file_library.schemas import (
    EventLibraryFileSchema, EventLibraryFileReadArgsSchema)

from queueapp.thumbnail_tasks import convert_file_into_thumbnail


# main input and output schema
event_library_file_schema = EventLibraryFileSchema()
# schema for reading get arguments
event_library_file_read_schema = EventLibraryFileReadArgsSchema(strict=True)


class EventLibraryFileAPI(AuthResource):
    """
    Create, update, delete API for Event library files
    """
    @swag_from('swagger_docs/event_file_library_post.yml')
    def post(self):
        """
        Create a file
        """
        json_data = {}
        try:
            # validate and deserialize input into object
            data, errors = event_library_file_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.account_id = g.current_user['account_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        file_data = {'files': {}, 'types': {}}
        sub_folder = data.file_subfolder_name()
        full_folder = data.full_folder_path()

        if 'filename' in request.files:
            # new file being added
            # add new file
            fpath, fname, ferrors, ftype = store_file(
                eventfile, request.files['filename'], sub_folder=sub_folder,
                full_folder=full_folder, detect_type=True,
                type_only=True, not_local=True)
            if ferrors:
                db.session.delete(data)
                db.session.commit()
                return ferrors['message'], ferrors['code']
            file_data['files'][fname] = fpath
            file_data['types'][fname] = ftype
        else:
            db.session.delete(data)
            db.session.commit()
            c_abort(400, message='No file provided')

        try:
            if file_data and (file_data['files'] or 'delete' in file_data):
                # populate db data from file_data
                # parse new files
                if file_data['files']:
                    data.filename = [fname for fname in file_data['files']][0]
                    data.file_type = file_data['types'][data.filename]

            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
            # task call for thumbnail generation
            if file_type_for_thumbnail(fname):
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_EVENT, fpath).delay()
            else:
                delete_fs_file(fpath)
        except HTTPException as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            raise e
        except Exception as e:
            db.session.rollback()
            db.session.delete(data)
            db.session.commit()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'File Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update a archive file, pass file data as multipart-form
        """
        # #TODO: implement in future
        pass

    @swag_from('swagger_docs/event_file_library_delete.yml')
    def delete(self, row_id):
        """
        Delete a file
        """
        model = None
        try:
            # first find model
            model = EventLibraryFile.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)

            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()
            # delete file from s3
            # #TODO:used in future
            # fully_delete_file.s(True, model.row_id).delay()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/event_file_library_get.yml')
    def get(self, row_id):
        """
        Get a file by id
        """
        model = None
        try:
            # first find model
            model = EventLibraryFile.query.options(joinedload(
                EventLibraryFile.account)).get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = event_library_file_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class EventLibraryFileListAPI(AuthResource):
    """
    Read API for Event library file lists, i.e, more than 1 library file
    """
    model_class = EventLibraryFile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['filename_url']
        super(EventLibraryFileListAPI, self).__init__(*args, **kwargs)

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
            EventLibraryFile.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.options(joinedload(EventLibraryFile.account))

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/event_file_library_get_list.yml')
    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            event_library_file_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(EventLibraryFile), operator)
            # making a copy of the main output schema
            event_library_file_schema = EventLibraryFileSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                event_library_file_schema = EventLibraryFileSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching files found')
            result = event_library_file_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
