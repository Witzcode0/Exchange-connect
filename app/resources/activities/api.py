"""
Api for Global activities
"""

from werkzeug.exceptions import HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy import func, desc, asc, literal_column
from sqlalchemy.orm import load_only, aliased
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.auth.decorators import role_permission_required
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from app.resources.account_profiles.models import AccountProfile
from app.resources.activities.schemas import (
    GlobalActivityReadArgsSchema, GlobalActitvitySchema)
from app.resources.activities import constants as ACTIVITY
from app.corporate_access_resources.corporate_access_events.models import\
    CorporateAccessEvent
from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.resources.activities.helper import insert_url
from app.resources.roles import constants as ROLE


class GlobalActivityGetListApi(AuthResource):
    """
    Read API for global activities lists, i.e, more than
    """

    def __init__(self, *args, **kwargs):
        super(GlobalActivityGetListApi, self).__init__(*args, **kwargs)

    def build_query(self, filters, pfields, sort, pagination, query_session,
                    operator, include_deleted=False):
        """
        Builds the query by calling parent helpers _build_query,
        _build_final_query
        Also manages extra_filters (combined filters) here if any
        """
        query_filters, extra_query, db_projection, s_projection, order, \
            paging = self._build_query(
                filters, pfields, sort, pagination, operator,
                include_deleted=include_deleted)

        # build specific extra queries filters
        if filters:
            pass

        creator = aliased(UserProfile, name='creator')
        modifier = aliased(UserProfile, name='modifier')
        user_fullname = func.concat(
            func.lower(UserProfile.first_name),
            ' ',
            func.lower(UserProfile.last_name)).label('name')
        creator_fullname = func.concat(
            func.lower(creator.first_name), ' ', func.lower(
                creator.last_name)).label('creator_name')
        modifier_fullname = func.concat(
            func.lower(modifier.first_name), ' ', func.lower(
                modifier.last_name)).label('modifier_name')

        # for user profile activity
        user_profile_session = db.session.query(
            UserProfile.row_id.label('row_id'), user_fullname,
            UserProfile.created_date.label('created_date'),
            UserProfile.modified_date.label('modified_date'),
            func.concat(ACTIVITY.USERPROFILE).label('activity_type'),
            creator_fullname, modifier_fullname).\
            join(
                User, UserProfile.user_id == User.row_id, isouter=True).\
            join(Account, Account.row_id == UserProfile.account_id,
                 isouter=True).\
            join(
                creator, creator.user_id == User.created_by, isouter=True).\
            join(
                modifier, modifier.user_id == User.updated_by, isouter=True)

        user_profile_query = self._build_final_query(
            query_filters, user_profile_session, operator,
            main_class=UserProfile)

        # for account activity
        account_session = db.session.query(
            AccountProfile.row_id.label('row_id'),
            Account.account_name.label('name'),
            AccountProfile.created_date.label('created_date'),
            AccountProfile.modified_date.label('modified_date'),
            func.concat(ACTIVITY.ACCOUNTPROFILE).label('activity_type'),
            creator_fullname, modifier_fullname).\
            join(Account, Account.row_id == AccountProfile.account_id,
                 isouter=True).\
            join(
                creator, creator.user_id == Account.created_by, isouter=True).\
            join(
                modifier, modifier.user_id == Account.updated_by, isouter=True)

        account_query = self._build_final_query(
            query_filters, account_session, operator,
            main_class=AccountProfile)

        # for corporate access event activity
        corporate_session = db.session.query(
            CorporateAccessEvent.row_id.label('row_id'),
            CorporateAccessEvent.title.label('name'),
            CorporateAccessEvent.created_date.label('created_date'),
            CorporateAccessEvent.modified_date.label('modified_date'),
            func.concat(ACTIVITY.CORPORATE).label('activity_type'),
            creator_fullname, modifier_fullname).\
            join(
                creator, creator.user_id == CorporateAccessEvent.created_by,
                isouter=True).\
            join(
                modifier, modifier.user_id == CorporateAccessEvent.updated_by,
                isouter=True)

        corporate_query = self._build_final_query(
            query_filters, corporate_session, operator,
            main_class=CorporateAccessEvent)

        # for webcast activity
        webcast_session = db.session.query(
            Webcast.row_id.label('row_id'), Webcast.title.label('name'),
            Webcast.created_date.label('created_date'),
            Webcast.modified_date.label('modified_date'),
            func.concat(ACTIVITY.WEBCAST).label('activity_type'),
            creator_fullname, modifier_fullname).\
            join(
                creator, creator.user_id == Webcast.created_by,
                isouter=True).\
            join(
                modifier, modifier.user_id == Webcast.updated_by,
                isouter=True)

        webcast_query = self._build_final_query(
            query_filters, webcast_session, operator, main_class=Webcast)

        # for webinar activity
        webinar_session = db.session.query(
            Webinar.row_id.label('row_id'), Webinar.title.label('name'),
            Webinar.created_date.label('created_date'),
            Webinar.modified_date.label('modified_date'),
            func.concat(ACTIVITY.WEBINAR).label('activity_type'),
            creator_fullname, modifier_fullname).\
            join(
                creator, creator.user_id == Webinar.created_by,
                isouter=True).\
            join(
                modifier, modifier.user_id == Webinar.updated_by,
                isouter=True)

        webinar_query = self._build_final_query(
            query_filters, webinar_session, operator, main_class=Webinar)

        query_union = account_query.union_all(
            user_profile_query, corporate_query, webcast_query,
            webinar_query)
        if sort:
            sort_fxn = asc
            if sort['sort'] == 'dsc':
                sort_fxn = desc
            if 'name' in sort['sort_by']:
                order.append(sort_fxn('name'))
            if 'activity_type' in sort['sort_by']:
                order.append(sort_fxn('activity_type'))
        order.append(desc('modified_date'))
        name = filters.get('name', None)
        if name:
            query_union = query_union.filter(
                func.lower(literal_column('name')).like(
                    '%{}%'.format(name.lower())))
        return query_union, db_projection, s_projection, order, paging

    @role_permission_required(perms=[ROLE.EPT_NU], roles=[
        ROLE.ERT_SU, ROLE.ERT_MNG, ROLE.ERT_AD])
    @swag_from('swagger_docs/activities_get_list.yml')
    def get(self):
        """
        Get the list
        """
        global_activity_read_schema = GlobalActivityReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            global_activity_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging = \
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(UserProfile), operator)
            # making a copy of the main output schema
            global_activity_schema = GlobalActitvitySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                global_activity_schema = GlobalActitvitySchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching activities found')
            result = global_activity_schema.dump(models, many=True)
            # get link from here
            result_url = insert_url(result.data)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
