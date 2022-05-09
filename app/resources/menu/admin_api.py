"""
API endpoints for "menu" package.
"""
from flask import request, current_app
from flask_restful import abort
from werkzeug.exceptions import Forbidden, HTTPException
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.resources.menu.models import Menu
from app.resources.menu.schemas import MenuSchema, MenuCreateSchema
from app.base.api import AuthResource
from app.base import constants as APP
from app.resources.menu.schemas import MenuReadArgSchema

from app.resources.menu.helpers import (
    load_child_menu_objects, keep_only_active_menus)
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE


class MenuAPI(AuthResource):
    """
    Post API for contact us inquiries
    """

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/menu_post.yml')
    def post(self):
        """
        Create a menu
        """
        menu_schema = MenuCreateSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = menu_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            db.session.add(data)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Menu added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/menu_put.yml')
    def put(self, row_id):
        """
        Update menu by row_id
        """
        menu_schema = MenuSchema()
        model = None
        try:
            model = Menu.query.get(row_id)
            if model is None:
                c_abort(404, message='Menu id: %s'
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
            # validate and deserialize input
            data, errors = menu_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)

            db.session.add(data)
            # sequence of child menus will also be updated if present
            if 'child_menus' in json_data and json_data['child_menus']:
                for menu in json_data['child_menus']:
                    sequence_json = {'sequence': menu['sequence']}
                    model = Menu.query.get(menu['row_id'])
                    if model:
                        data, errors = menu_schema.load(
                            sequence_json, instance=model, partial=True)
                        if errors:
                            c_abort(422, errors=errors)
                        db.session.add(data)
            # no errors, so add data to db
            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Menu id: %s' %
                           str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/menu_delete.yml')
    def delete(self, row_id):
        """
        Delete a menu by row_id
        """
        try:
            # first find model
            model = Menu.query.get(row_id)
            if model is None:
                c_abort(404, message='Menu id: %s'
                                     ' does not exist' % str(row_id))
            # if model is found, and not yet deleted, delete it
            db.session.delete(model)
            Menu.query.filter(
                Menu.parent_id == model.parent_id,
                Menu.sequence > model.sequence).update({
                'sequence': Menu.sequence - 1})
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
        ROLE.ERT_SU, ROLE.ERT_CA,
        ROLE.ERT_MNG])
    @swag_from('swagger_docs/menu_get.yml')
    def get(self, row_id):
        """
        Get a menu by id
        """
        result = None
        menu_schema = MenuSchema()
        try:
            # first find model
            model = Menu.query.get(row_id)
            if model is None:
                c_abort(404, message='Menu id: %s'
                                     ' does not exist' % str(row_id))
            result = menu_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class MenuListAPI(AuthResource):
    """
    Read API for menu lists, i.e, more than 1 menu
    """
    model_class = Menu

    def __init__(self, *args, **kwargs):
        super(MenuListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        if not filters['parent_id']:
            filters['parent_id'] = None
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        query = self._build_final_query(
            query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/menu_get_list.yml')
    def get(self):
        """
        Get the list of menu by admin
        """
        # schema for reading get arguments
        menu_read_schema = MenuReadArgSchema(
            strict=True)
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            menu_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Menu),
                                 operator)
            # making a copy of the main output schema
            menu_schema = MenuSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                menu_schema = MenuSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            if not models:
                c_abort(404, message='No matching menus found')
            result = menu_schema.dump(models, many=True)
            if filters['only_active']:
                keep_only_active_menus(result.data)
            total = len(result.data)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200


class BulkMenuUpdate(AuthResource):

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    # @swag_from('swagger_docs/bulk_menu_put.yml')
    def put(self):
        """
        Update all menus
        """
        menu_schema = MenuSchema()

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:

            all_menus = json_data['menus']
            menu_models = []

            def _get_menu_models(menus):
                for menu in menus:
                    model = Menu.query.get(menu['row_id'])
                    if not model:
                        c_abort(
                            422, message="menu {} doesn't exist".format(
                                menu['row_id']
                            ))
                    # validate and deserialize input
                    data, errors = menu_schema.load(
                        menu, instance=model, partial=True)
                    if errors:
                        c_abort(422, errors=errors)
                    menu_models.append(data)

                    if menu['child_menus']:
                        _get_menu_models(menu['child_menus'])

            # no errors, so add data to db
            _get_menu_models(all_menus)
            db.session.add_all(menu_models)

            db.session.commit()
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (country_id, state_id, city_name)=(1, 1, Hyd)
                # already exists.
                column = e.orig.diag.message_detail.split('(')[2].split(':')[0]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            current_app.logger.exception(e)
            abort(500)

        return {'message': "all menus updated"}, 200