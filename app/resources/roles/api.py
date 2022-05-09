"""
API endpoints for "role" package.
"""

from werkzeug.exceptions import HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role, RoleMenuPermission
from app.resources.roles.schemas import (
    RoleSchema, RoleReadArgsSchema)
from app.resources.roles.helpers import (
    get_role_menu_perms_object, add_permissions_to_menus)
from app.base import constants as APP
from app.resources.menu.models import Menu
from app.resources.menu.schemas import MenuSchema
from app.resources.menu.helpers import keep_only_active_menus
from app.resources.users.models import User


class RoleAPI(AuthResource):
    """
    Create, update, delete API for roles
    """

    @role_permission_required(perms=[ROLE.EPT_CR], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/role_post.yml')
    def post(self):
        """
        Create a role
        """

        role_schema = RoleSchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            menus = []
            if 'menus' in json_data:
                menus = json_data.pop('menus')

            # validate and deserialize input into object
            data, errors = role_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()
            rmps = get_role_menu_perms_object(data.row_id, menus)
            db.session.add_all(rmps)

            if not data.permissions:
                data.permissions = []
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(analyst) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
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

        return {'message': 'Role Added: %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @role_permission_required(perms=[ROLE.EPT_CR], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/role_put.yml')
    def put(self, row_id):
        """
        Update a role
        """

        role_schema = RoleSchema()
        # first find model
        model = None
        try:
            model = Role.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Role id: %s does not exist' %
                                     str(row_id))

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
            # name and account_type of default role can not be changed
            if model.is_default():
                json_data.pop('name', None)
                json_data.pop('account_type', None)

            menus = None
            if 'menus' in json_data:
                menus = json_data['menus']
            # validate and deserialize input
            data, errors = role_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # check that permissions are not changed by anyone other than SA
            if (set(model.permissions) != set(data.permissions) and
                    g.current_user['role']['name'] != ROLE.ERT_SU):
                c_abort(403, message='Role permissions can not be edited')
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            if not data.permissions:
                data.permissions = []
            db.session.add(data)

            if menus is not None:
                RoleMenuPermission.query.filter_by(
                    role_id=data.row_id).delete()
                rmps = get_role_menu_perms_object(data.row_id, menus)
                db.session.add_all(rmps)
            # logout all the users who have this role assigned
            User.query.filter_by(role_id=data.row_id).update({
                'token_valid': False, 'token_valid_mobile': False
            }, synchronize_session=False)
            db.session.commit()
        except IntegrityError as e:
            current_app.logger.exception(e)
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (name)=(analyst) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
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
        return {'message': 'Updated Role id: %s' % str(row_id)}, 200

    @role_permission_required(perms=[ROLE.EPT_CR], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/role_delete.yml')
    def delete(self, row_id):
        """
        Delete a role
        """

        model = None
        try:
            # first find model
            model = Role.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Role id: %s does not exist' %
                                     str(row_id))
            if model.is_default():
                c_abort(403, message='Role id: %s can not be deleted' %
                                     str(row_id))

            # if model is found, and not yet deleted, delete it
            model.deleted = True
            db.session.add(model)
            db.session.commit()
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @role_permission_required(perms=[ROLE.EPT_AR], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/role_get.yml')
    def get(self, row_id):
        """
        Get a role by id
        """

        role_schema = RoleSchema()
        try:
            # first find model
            model = Role.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Role id: %s does not exist' %
                                     str(row_id))

            result = role_schema.dump(model).data
            role_perms = result['role_menu_permissions']
            menu_ids = [x['menu']['row_id'] for x in role_perms]
            menus = Menu.query.filter(
                Menu.row_id.in_(menu_ids),
                Menu.parent_id.is_(None)).order_by('sequence').all()
            menus = MenuSchema(many=True).dump(menus).data
            menu_perms = result.pop('role_menu_permissions')
            add_permissions_to_menus(menus, menu_perms, False)
            keep_only_active_menus(menus)
            result['menus'] = menus

        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class RoleList(AuthResource):
    """
    Read API for roles lists, i.e, more than 1 role
    """

    model_class = Role

    def __init__(self, *args, **kwargs):
        super(RoleList, self).__init__(*args, **kwargs)

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

        # add extra filter if not super-admin, admin user and manager
        if g.current_user['role']['name'] not in [
                ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG]:
            query_filters['base'].append(~Role.name.in_(
                [ROLE.ERT_SU, ROLE.ERT_AD, ROLE.ERT_MNG]))
        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AR], roles=[ROLE.ERT_SU])
    @swag_from('swagger_docs/role_get_list.yml')
    def get(self):
        """
        Get the list
        """

        role_read_schema = RoleReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            role_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Role), operator)
            # making a copy of the main output schema
            role_schema = RoleSchema(exclude=['role_menu_permissions'])
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                role_schema = RoleSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching roles found')
            result = role_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
