"""
API endpoints for "Ir Module API" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError
from marshmallow.exceptions import ValidationError
from app.base.api import AuthResource, BaseResource, load_current_user
from sqlalchemy import and_, any_, func, literal

from app.base import constants as APP
from app import db, c_abort, irmodulephotos
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.common.helpers import store_file, copy_file
from app.resources.ir_module.models import (
    IrModule,
    IrModuleHeading,
    favirmodule)
from app.resources.ir_module.schemas import (
    IrModuleSchema,
    IrModuleHeadingSchema,
    IrModuleReadArgsSchema,
    IrModuleHeadingReadArgsSchema)

from queueapp.thumbnail_tasks import convert_file_into_thumbnail


class IrModuleAPI(AuthResource):
    """
    post, edit, delete and get for ir module
    """
    def post(self):
        """
        Create ir module
        """
        ir_module_schema = IrModuleSchema()
        try:
            if request.form:
                json_data = request.form.to_dict()
                data, errors = ir_module_schema.load(json_data)
                if errors:
                    c_abort(422, errors=errors)

                # no errors, so add data to db
                if g.current_user['row_id']:
                    data.created_by = g.current_user['row_id']
                    data.updated_by = data.created_by
                db.session.add(data)
                db.session.commit()
            profile_data = {'files': {}}
            profile_path = None
            sub_folder = data.file_subfolder_name()
            profile_full_folder = data.full_folder_path(
                IrModule.root_profile_photo_folder_key)
            try:
                # save files
                if 'infoghraphic' in request.files:
                    profile_path, profile_name, ferrors = store_file(
                        irmodulephotos, request.files['infoghraphic'],
                        sub_folder=sub_folder, full_folder=profile_full_folder,
                        not_local=True)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    profile_data['files'][profile_name] = profile_path
                # profile photo upload
                if profile_data and profile_data['files']:
                    # parse new files
                    if profile_data['files']:
                        data.infoghraphic = [
                            profile_name for profile_name
                            in profile_data['files']][0]
                db.session.commit()
            except HTTPException as e:
                raise e
            except Exception as e:
                current_app.logger.exception(e)
                abort(500)
            # generate thumbnail for profile photo
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_IR_MODULE_PHOTO,
                    profile_path, 'profile').delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
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

        return {'message': 'IR Module Created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update ir module
        """
        ir_module_schema = IrModuleSchema()

        model = None
        try:
            model = IrModule.query.get(row_id)
            if model is None:
                c_abort(404, message='IR Module id: %s'
                                     ' does not exist' % str(row_id))
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        # json_data = request.get_json()
        # if not json_data:
        #     c_abort(400)
        profile_data = {'files': {}}
        profile_path = None
        sub_folder = model.file_subfolder_name()
        profile_full_folder = model.full_folder_path(
            IrModule.root_profile_photo_folder_key)

        # save files
        if 'infoghraphic' in request.files:
            profile_path, profile_name, ferrors = store_file(
                irmodulephotos, request.files['infoghraphic'],
                sub_folder=sub_folder, full_folder=profile_full_folder,
                not_local=True)
            if ferrors:
                return ferrors['message'], ferrors['code']
            profile_data['files'][profile_name] = profile_path

        # delete files
        if 'infoghraphic' in request.form:
            profile_data['delete'] = []
            if request.form['infoghraphic'] == model.infoghraphic:
                profile_data['delete'].append(
                    request.form['infoghraphic'])
                if profile_data['delete']:
                    # delete all mentioned files
                    ferrors = delete_files(
                        profile_data['delete'], sub_folder=sub_folder,
                        full_folder=profile_full_folder)
                    if ferrors:
                        return ferrors['message'], ferrors['code']
                    # when profile photo delete profile thumbnail also delete
                    if model.profile_thumbnail:
                        th_errors = delete_files(
                            [model.profile_thumbnail],
                            sub_folder=sub_folder,
                            full_folder=profile_full_folder,
                            is_thumbnail=True)
                        if th_errors:
                            return th_errors['message'], th_errors['code']
        try:
            json_data = request.form.to_dict()
            data, errors = ir_module_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()

            # add user and ir_module if favourite is true
            if 'favourite' in json_data:
                fav_obj = db.session.query(favirmodule).filter(
                    favirmodule.user_id == g.current_user['row_id'],
                    favirmodule.ir_module_id == data.row_id).first()
                if json_data['favourite'] == 'true':
                    if not fav_obj:
                        db.session.add(favirmodule(
                            user_id=g.current_user['row_id'],
                            ir_module_id=data.row_id))
                        db.session.commit()
                else:
                    if fav_obj:
                        db.session.delete(fav_obj)
                        db.session.commit()

            # profile photo upload
            if profile_data and (
                    profile_data['files'] or 'delete' in profile_data):
                # parse new files
                if profile_data['files']:
                    data.infoghraphic = [
                        profile_name for profile_name
                        in profile_data['files']][0]
                # any old files to delete
                if 'delete' in profile_data:
                    for profile_name in profile_data['delete']:
                        if profile_name == data.infoghraphic:
                            data.infoghraphic = None
                            data.profile_thumbnail = None
            db.session.add(data)
            db.session.commit()
            if profile_path:
                convert_file_into_thumbnail.s(
                    True, data.row_id, APP.MOD_IR_MODULE_PHOTO,
                    profile_path, 'profile').delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
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

        return {'message': 'Update ir module id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a ir module
        """
        model = None
        try:
            # first find model
            model = IrModule.query.get(row_id)
            if model is None:
                c_abort(404, message='ir_module id: %s'
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

    def get(self, row_id):
        """
        Get a ir module request by id
        """
        model = None
        try:
            # first find model
            model = IrModule.query.get(row_id)
            if model is None:
                c_abort(404, message='ir_module id: %s'
                                     ' does not exist' % str(row_id))
            result = IrModuleSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class IrModuleListAPI(AuthResource):
    """
    Read API for ir module, i.e, more than 1
    """
    model_class = IrModule

    def __init__(self, *args, **kwargs):
        super(IrModuleListAPI, self).__init__(*args, **kwargs)

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

        module_name = None
        favourite = False

        if extra_query:
            if "module_name" in extra_query and extra_query['module_name']:
                module_name = extra_query.pop('module_name')
                query_filters['filters'].append(IrModule.module_name == module_name)
            if "favourite" in extra_query and extra_query['favourite']:
                favourite = True

        query = self._build_final_query(
            query_filters, query_session, operator)

        fav_query = query.join(
            favirmodule, favirmodule.ir_module_id==IrModule.row_id).filter(
            favirmodule.user_id == g.current_user['row_id'])

        list_fav = [m.row_id for m in fav_query]

        # favourite ir module query
        final_fav_query=fav_query.order_by(*order)

        if not favourite:
            ''' if favourite filter is false'''

            # normal ir module query
            nr_query=query.filter(~IrModule.row_id.in_(list_fav)).order_by(*order)

            # union both query
            final_query = final_fav_query.union_all(nr_query)
        else:
            ''' favourite filter is true'''
            final_query = final_fav_query

        return final_query, db_projection, s_projection, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            IrModuleReadArgsSchema(strict=True))

        try:
            # build the sql query
            query, db_projection, s_projection, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(IrModule),
                                 operator)

            # making a copy of the main output schema
            ir_module_schema = IrModuleSchema(exclude=['headings'])
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ir_module_schema = IrModuleSchema(
                    only=s_projection)
            # make query
            full_query = query.paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ir modules found')
            result = ir_module_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class IrModuleHeadingAPI(AuthResource):
    """
    post, edit, delete and get for ir module heading
    """ 
    def post(self):
        """
        Create ir module heading
        """
        ir_module_heading_schema = IrModuleHeadingSchema()

        json_data = request.get_json()
        # get the form data from the request
        if not json_data:
            c_abort(400)

        try:
            data, errors = ir_module_heading_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            # no errors, so add data to db
            if g.current_user['row_id']:
                data.created_by = g.current_user['row_id']
                data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
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

        return {'message': 'IR Module Heading Created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update ir module heading
        """
        ir_module_heading_schema = IrModuleHeadingSchema()

        model = None
        try:
            model = IrModuleHeading.query.get(row_id)
            if model is None:
                c_abort(404, message='IR Module heading id: %s'
                                     ' does not exist' % str(row_id))
        except Forbidden as e:
            raise e
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
            data, errors = ir_module_heading_schema.load(
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
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                column = e.orig.diag.message_detail.split('(')[1][:-2]
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

        return {'message': 'Update IR Module Heading id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a ir module
        """
        model = None
        try:
            # first find model
            model = IrModuleHeading.query.get(row_id)
            if model is None:
                c_abort(404, message='IR Module heading id: %s'
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

    def get(self, row_id):
        """
        Get a ir module request by id
        """
        model = None
        try:
            # first find model
            model = IrModuleHeading.query.get(row_id)
            if model is None:
                c_abort(404, message='IR Module heading id: %s'
                                     ' does not exist' % str(row_id))
            result = IrModuleHeadingSchema().dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class IrModuleHeadingListAPI(AuthResource):
    """
    Read API for ir module heading, i.e, more than 1
    """
    model_class = IrModuleHeading

    def __init__(self, *args, **kwargs):
        super(IrModuleHeadingListAPI, self).__init__(*args, **kwargs)

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

        ir_module_id = None
        deactivated = None

        if extra_query:
            if "ir_module_id" in extra_query and extra_query['ir_module_id']:
                ir_module_id = extra_query.pop('ir_module_id')
                query_filters['filters'].append(IrModuleHeading.ir_module_id == ir_module_id)
            if "deactivated" in extra_query:
                deactivated = extra_query.pop['deactivated']
                query_filters['filters'].append(IrModuleHeading.deactivated == deactivated)

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    def get(self):
        """
        Get the list
        """
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            IrModuleHeadingReadArgsSchema(strict=True))

        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(IrModuleHeading),
                                 operator)

            # making a copy of the main output schema
            ir_module_heading_schema = IrModuleHeadingSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ir_module_heading_schema = IrModuleHeadingSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ir modules found')
            result = ir_module_heading_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200