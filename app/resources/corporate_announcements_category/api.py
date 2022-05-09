from werkzeug.exceptions import HTTPException
from flask import request, current_app
from flask_restful import abort
from sqlalchemy.orm import load_only
from sqlalchemy.inspection import inspect

from app import (db, c_abort)
from app.base.api import AuthResource
from app.resources.corporate_announcements_category.models import (
    CorporateAnnouncementCategory)
from app.resources.corporate_announcements_category.schemas import (
    CorporateAnnouncementCategoryReadArgsSchema,
    CorporateAnnouncementCategoriesSchema)



class CorporateAnnouncementCategoryListAPI(AuthResource):
    """
    Read API for Category lists, i.e, more than 1 Category
    """
    model_class = CorporateAnnouncementCategory

    def __init__(self, *args, **kwargs):
        super(
            CorporateAnnouncementCategoryListAPI, self).__init__(*args, **kwargs)

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
        query_filters, extra_query, db_projection, s_projection, order, \
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

    def get(self):
        """
        Get the list by user
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
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CorporateAnnouncementCategory),
                                 operator)
            # making a copy of the main output schema
            admin_corporate_schema = CorporateAnnouncementCategoriesSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                admin_corporate_schema = CorporateAnnouncementCategoriesSchema(
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