"""
API endpoints for "corporate announcements category" package.
"""
from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy import and_, func
from sqlalchemy.orm import load_only, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.inspection import inspect
from flasgger import swag_from

from app import (
    db, c_abort, corporateannouncementfile, corporateannouncementxmlfile)
from app.base.api import AuthResource
from app.base import constants as APP
from app.auth.decorators import role_permission_required
from app.resources.corporate_announcements_category.models import (
    CorporateAnnouncementCategory)
from app.resources.corporate_announcements_category.schemas import (
    AdminCorporateAnnouncementCategorySchema,
    CorporateAnnouncementCategoryReadArgsSchema)
from app.resources.roles import constants as ROLE


class AdminCorporationCategoryAPI(AuthResource):
    """
    For add category and keywords for that
    """
    def post(self):
        """
        Create corporate announcement category by admin
        """
        admin_corporate_category_schema = AdminCorporateAnnouncementCategorySchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = admin_corporate_category_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by

            db.session.add(data)
            db.session.commit()

        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Corporate Announcement Category created: %s' %
                           str(data.row_id), 'row_id': data.row_id}, 201

    def put(self, row_id):
        """
        Update Corporate announcement by admin
        """

        admin_corporate_category_schema = AdminCorporateAnnouncementCategorySchema()
        model = None
        try:
            model = CorporateAnnouncementCategory.query.get(row_id)

            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
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
            data, errors = admin_corporate_category_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
        except Forbidden as e:
            raise e
        except IntegrityError as e:
            # format of the message:
            # Key (account_id)=(17) is not present in table account
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message=APP.MSG_DOES_NOT_EXIST, errors={
                    column: [APP.MSG_DOES_NOT_EXIST]})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        return {'message': 'Updated Corporate Announcement category id: %s' %
                           str(row_id)}, 200

    def delete(self, row_id):
        """
        Delete a corporate announcement category by admin
        """
        model = None
        try:
            # first find model
            model = CorporateAnnouncementCategory.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                        ' does not exist' % str(row_id))
            # if model is found, and not yet deleted, delete it
            model.updated_by = g.current_user['row_id']
            model.deleted = True
            db.session.add(model)
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
        Get a corporate announcement Category request by id by admin
        """
        admin_corporate_category_schema = AdminCorporateAnnouncementCategorySchema()
        model = None
        try:
            # first find model
            model = CorporateAnnouncementCategory.query.get(row_id)
            if model is None or model.deleted:
                c_abort(404, message='Corporate Announcement id: %s'
                                     ' does not exist' % str(row_id))
            result = admin_corporate_category_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class AdminCorporateAnnouncementCategoryListAPI(AuthResource):
    """
    Read API for Category lists, i.e, more than 1 Category
    """
    model_class = CorporateAnnouncementCategory

    def __init__(self, *args, **kwargs):
        super(
            AdminCorporateAnnouncementCategoryListAPI, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        category = None
        if 'category' in filters and filters['category']:
            category = filters.pop('category')
        query_filters, extra_query, db_projection, s_projection, order,\
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)
        mapper = inspect(CorporateAnnouncementCategory)
        # build specific extra queries filters
        account_id = None
        
        query = self._build_final_query(
            query_filters, query_session, operator)

        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())

        return query, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_AA], roles=[
        ROLE.ERT_SU, ROLE.ERT_CA, ROLE.ERT_MNG])
    @swag_from('swagger_docs/admin_corporate_announcement_get_list.yml')
    def get(self):
        """
        Get the list by admin
        """
        # schema for reading get arguments
        admin_corporate_category_read_schema = CorporateAnnouncementCategoryReadArgsSchema(
            strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_corporate_category_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAnnouncementCategory),
                                 operator)
            # making a copy of the main output schema
            admin_corporate_schema = AdminCorporateAnnouncementCategorySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_corporate_schema = AdminCorporateAnnouncementCategorySchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate'
                                     ' announcement found')
            result = admin_corporate_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200

