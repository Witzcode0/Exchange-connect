"""
API endpoints for "crm distribution file library" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from flasgger.utils import swag_from

from app import db, c_abort, crmdistlibraryfile
from app.base.api import AuthResource, BaseResource
from app.base import constants as APP
from app.common.helpers import store_file, delete_files
from app.crm_resources.crm_distribution_file_library.models import (
    CRMDistributionLibraryFile)
from app.crm_resources.crm_distribution_file_library.schemas import (
    CRMDistributionLibraryFileSchema, CRMLibraryFileReadArgsSchema)


class CRMDistributionLibraryFileAPI(AuthResource):
    """
    Create, update, delete API for CRM library files
    """

    def post(self):
        """
        Create a file
        """
        # main input and output schema
        crm_library_file_schema = CRMDistributionLibraryFileSchema()

        json_data = request.form
        try:
            # validate and deserialize input into object
            data, errors = crm_library_file_schema.load(json_data)
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
                crmdistlibraryfile, request.files['filename'],
                sub_folder=sub_folder, full_folder=full_folder,
                detect_type=True, type_only=True, acl='public-read')
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
            data.load_urls()
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
                'row_id': data.row_id,
                'file_url': data.file_url,
                'filename': data.filename}, 201

    def put(self, row_id):
        """
        Update a archive file, pass file data as multipart-form
        """
        # #TODO: implement in future
        pass

    def delete(self, row_id):
        """
        Delete a file
        """
        model = None
        try:
            # first find model
            model = CRMDistributionLibraryFile.query.get(row_id)
            if model is None:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            sub_folder = model.file_subfolder_name()
            file_full_folder = model.full_folder_path(
                model.root_folder_key)
            delete_files(
                [model.filename], sub_folder=sub_folder,
                full_folder=file_full_folder, is_thumbnail=True)
            # if model is found, and not yet deleted, delete it
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
        Get a file by id
        """
        # main input and output schema
        crm_library_file_schema = CRMDistributionLibraryFileSchema()

        model = None
        try:
            # first find model
            model = CRMDistributionLibraryFile.query.options(joinedload(
                CRMDistributionLibraryFile.account)).get(row_id)
            if model is None:
                c_abort(404, message='File id: %s does not exist' %
                                     str(row_id))
            # check ownership
            if model.created_by != g.current_user['row_id']:
                abort(403)
            result = crm_library_file_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result}, 200


class CRMDistributionLibraryFileListAPI(AuthResource):
    """
    Read API for CRM library file lists, i.e, more than 1 library file
    """
    model_class = CRMDistributionLibraryFile

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['file_url']
        super(CRMDistributionLibraryFileListAPI, self).__init__(*args, **kwargs)

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
            CRMDistributionLibraryFile.created_by == g.current_user['row_id'])
        query = self._build_final_query(query_filters, query_session, operator)

        query = query.options(joinedload(CRMDistributionLibraryFile.account))

        return query, db_projection, s_projection, order, paging

    # @swag_from('swagger_docs/crm_file_library_get_list.yml')
    def get(self):
        """
        Get the list
        """
        # schema for reading get arguments
        crm_library_file_read_schema = CRMLibraryFileReadArgsSchema(
            strict=True)

        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            crm_library_file_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CRMDistributionLibraryFile),
                                 operator)
            # making a copy of the main output schema
            crm_library_file_schema = CRMDistributionLibraryFileSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                crm_library_file_schema = CRMDistributionLibraryFileSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching files found')
            result = crm_library_file_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
