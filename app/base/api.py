"""
Common functionalities for API, can include classes, functions.
"""

from flask import current_app, request
from flask_restful import Resource
from webargs.flaskparser import parser
from sqlalchemy import and_, or_
from sqlalchemy.orm import aliased
from sqlalchemy.inspection import inspect
from sqlalchemy.types import String, Enum, ARRAY
from flask_jwt_extended import jwt_required

from app.base.model_fields import ChoiceString, LCString
from app.resources.accounts.models import Account
from app.auth.decorators import load_current_user
from app.resources.account_profiles.models import AccountProfile
from app.resources.accounts.models import Account
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)


class SQLAQueryMixin(object):
    """
    A base mixin class for sqlalchemy query builders
    """
    model_class = None
    special_fields = ['links']  # any special field which could be used
    # for projections

    def __init__(self, *args, **kwargs):
        self.model_class = kwargs.pop('model_class', self.model_class)
        self.special_fields.extend(kwargs.pop('special_fields', []))
        super(SQLAQueryMixin, self).__init__(*args, **kwargs)

    def _build_query(self, filters, pfields, sort, pagination, operator,
                     include_deleted=False):
        """
        Builds the SQLAlchemy query filters, projections, sort, pagination
        """
        query_filters = {'base': [], 'filters': []}
        # the base and filters will always be and_
        # combination of filters themselves will be dependent on operator
        extra_query = {}  # some possible combined filters
        db_projection = []
        s_projection = []
        order = []
        paging = pagination
        if not self.model_class:
            # special cases, just return defaults
            return (query_filters, extra_query, db_projection, s_projection,
                    order, paging)

        mapper = inspect(self.model_class)
        # some models could have a deleted flag
        if 'deleted' in mapper.columns and not include_deleted:
            query_filters['base'].append(mapper.columns['deleted'].is_(False))
        # first identify the filters
        if filters:
            for f in filters:
                if f in mapper.columns:
                    # for enum strings use equal
                    if isinstance(mapper.columns[f].type, Enum):
                        query_filters['filters'].append(
                            mapper.columns[f] == filters[f])
                        continue
                    # for the custom "ChoiceString" use its 'matching' value
                    if isinstance(mapper.columns[f].type, ChoiceString):
                        if mapper.columns[f].type.matching == 'exact':
                            query_filters['filters'].append(
                                mapper.columns[f] == filters[f])
                        else:
                            query_filters['filters'].append(
                                mapper.columns[f].ilike(
                                    '%%%s%%' % filters[f]))
                        continue
                    # for the custom "LCString" use ilike
                    if isinstance(mapper.columns[f].type, LCString):
                        query_filters['filters'].append(
                            mapper.columns[f].ilike('%%%s%%' % filters[f]))
                        continue
                    # for strings use ilike
                    if isinstance(mapper.columns[f].type, String):
                        query_filters['filters'].append(
                            mapper.columns[f].ilike('%%%s%%' % filters[f]))
                        continue
                    # for array use any
                    if isinstance(mapper.columns[f].type, ARRAY):
                        query_filters['filters'].append(
                            mapper.columns[f].any(filters[f]))
                        continue
                    # for everything else use equal
                    query_filters['filters'].append(
                        mapper.columns[f] == filters[f])
                else:
                    # build date query
                    if f == 'created_date_from' and filters[f]:
                        query_filters['filters'].append(
                            mapper.columns['created_date'] >= filters[f])
                        continue
                    if f == 'created_date_to' and filters[f]:
                        query_filters['filters'].append(
                            mapper.columns['created_date'] <= filters[f])
                        continue
                    extra_query[f] = filters[f]
        # identify the projections if any
        if pfields:
            for f in pfields:
                if f in mapper.columns:
                    db_projection.append(f)
            # any special schema only projections
            s_projection = db_projection[:]
            for spf in self.special_fields:
                if spf in pfields:
                    s_projection.append(spf)
        # identify ordering
        if sort:
            sort_fxn = 'asc'
            if sort['sort'] == 'dsc':
                sort_fxn = 'desc'
            for sby in sort['sort_by']:
                if sby in mapper.columns:
                    order.append(getattr(mapper.columns[sby], sort_fxn)())
        return (query_filters, extra_query, db_projection, s_projection,
                order, paging)

    def _build_final_query(self, query_filters, query_session, operator,
                           main_class=None, apply_domain_filter=True):
        """
        Builds the actual query, when passed the "query_filters" generated in
        "_build_query" and possibly "build_query" in child (when there are
        extra args)
        """
        # build actual query
        query = query_session
        final_filter = []
        if query_filters['filters']:
            if operator == 'and':
                op_fxn = and_
            elif operator == 'or':
                op_fxn = or_
            final_filter.append(op_fxn(*query_filters['filters']))
        if query_filters['base']:  # base filter will always be and_
            final_filter.append(and_(*query_filters['base']))
        if final_filter:
            query = query.filter(and_(*final_filter))
        domain_code = None
        include_blocked = False
        if ('Origin' in request.headers
                and 'admin' in request.headers['Origin']):
            domain_code = request.headers.get('Domain-Code')
            include_blocked = True
        # flag to know if request is from design lab front end
        # will not apply domain filter on it
        from_design_lab = False
        if ('Origin' in request.headers
                and 'designlab' in request.headers['Origin']):
            from_design_lab = True
        if ((self.model_class or main_class) and
                (domain_code or not include_blocked)):
            domain_name = get_domain_name(domain_code)
            domain_id, domain_config = get_domain_info(domain_name)
            main_class = self.model_class or main_class
            mapper = inspect(main_class)
            if main_class is Account and not include_blocked:
                query = query.filter(Account.blocked == False)
            if 'domain_id' in mapper.columns and apply_domain_filter:
                query = query.filter(main_class.domain_id == domain_id)
            elif 'account_id' in mapper.columns:
                aliased_account = aliased(Account)
                query = query.join(
                    aliased_account,
                    aliased_account.row_id == main_class.account_id)
                if not from_design_lab and apply_domain_filter:
                    query = query.filter(aliased_account.domain_id == domain_id)
                if not include_blocked:
                    query = query.filter(aliased_account.blocked == False)
        return query

    def _build_final_query_without_account_id(self, query_filters, query_session, operator,
                           main_class=None, apply_domain_filter=True):
        """
        Builds the actual query, when passed the "query_filters" generated in
        "_build_query" and possibly "build_query" in child (when there are
        extra args)
        """
        # build actual query
        query = query_session
        final_filter = []
        if query_filters['filters']:
            if operator == 'and':
                op_fxn = and_
            elif operator == 'or':
                op_fxn = or_
            final_filter.append(op_fxn(*query_filters['filters']))
        if query_filters['base']:  # base filter will always be and_
            final_filter.append(and_(*query_filters['base']))
        if final_filter:
            query = query.filter(and_(*final_filter))
        domain_code = None
        include_blocked = False
        if ('Origin' in request.headers
                and 'admin' in request.headers['Origin']):
            domain_code = request.headers.get('Domain-Code')
            include_blocked = True
        # flag to know if request is from design lab front end
        # will not apply domain filter on it
        from_design_lab = False
        if ('Origin' in request.headers
                and 'designlab' in request.headers['Origin']):
            from_design_lab = True
        if ((self.model_class or main_class) and
                (domain_code or not include_blocked)):
            domain_name = get_domain_name(domain_code)
            domain_id, domain_config = get_domain_info(domain_name)
            main_class = self.model_class or main_class
            mapper = inspect(main_class)
            if main_class is Account and not include_blocked:
                query = query.filter(Account.blocked == False)
            if 'domain_id' in mapper.columns and apply_domain_filter:
                query = query.filter(main_class.domain_id == domain_id)
        return query


class BaseResource(SQLAQueryMixin, Resource):
    """
    Has some common functionality required across APIs.
    """

    def __init__(self, *args, **kwargs):
        super(BaseResource, self).__init__(*args, **kwargs)

    def parse_args(self, read_schema):
        """
        Parses the request arguments for field filters, sort and pagination
        """
        try:
            input_data = parser.parse(read_schema, locations=('querystring',))
        except Exception as e:
            current_app.logger.exception(e)
            raise e

        # all good with incoming data, so continue
        filters = {}
        pfields = []
        sort = {}
        pagination = {}  # per_page, page number
        operator = ''
        if not input_data:
            return filters, pfields, sort, pagination, operator

        # there are filter arguments, so parse them, and separate into
        # filters, sort, pagination
        for k in input_data:
            if k in ['sort_by', 'sort', 'per_page', 'page', 'categories']:
                # sort out sorting
                if k == 'sort':
                    sort['sort'] = input_data['sort']
                if k == 'sort_by':
                    sort['sort_by'] = input_data['sort_by']
                if k == 'categories':
                    filters['categories'] = input_data['categories']
                # sort out pagination
                if k == 'per_page':
                    try:
                        pagination['per_page'] = int(input_data['per_page'])
                    except Exception:
                        pagination['per_page'] = 20
                if k == 'page':
                    try:
                        pagination['page'] = int(input_data['page'])
                    except Exception:
                        pagination['page'] = 1
                continue
            # fields
            if k == 'pfields':
                if input_data['pfields']:
                    pfields = input_data['pfields']
                continue
            # operator
            if k == 'operator':
                operator = input_data[k]
                continue
            # filters
            if input_data[k] or input_data[k] is False or input_data[k] == 0:
                filters[k] = input_data[k]
        return filters, pfields, sort, pagination, operator


class AuthResource(BaseResource):
    """
    Adds authentication to the resouce
    """
    # order of decorators matters
    method_decorators = [load_current_user, jwt_required]
