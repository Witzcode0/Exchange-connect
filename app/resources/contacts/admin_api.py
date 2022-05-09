"""
API endpoints for "admin contacts" package.
"""

from werkzeug.exceptions import HTTPException
from flask import current_app
from flask_restful import abort
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import load_only, aliased
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from app.resources.contacts.models import Contact
from app.resources.contacts.schemas import (
    AdminContactReadArgsSchema, ContactSchema)


class AdminContactListAPI(AuthResource):
    """
    Read API for admin contact lists, i.e, more than 1 contact
    """
    model_class = Contact

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['sender', 'sendee', 'the_other']
        super(AdminContactListAPI, self).__init__(*args, **kwargs)

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
        full_name = ""
        user_id = None
        if extra_query:
            if "full_name" in extra_query and extra_query[
                    'full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'
            if "user_id" in extra_query and extra_query["user_id"]:
                user_id = extra_query["user_id"]
        if full_name == "":
            full_name = '%%'

        # append extra query filter to fetch contacts either send or receive

        query_filters['base'].append(
            or_(Contact.sent_by == user_id,
                Contact.sent_to == user_id))

        query = self._build_final_query(query_filters, query_session, operator)
        # eager load account and user profile table
        # #TODO: improve by loading only required fields of user profile,
        # right now, if we load only required fields, it is making many queries

        sender = aliased(User, name='sender')
        sendee = aliased(User, name='sendee')
        sender_profile = aliased(UserProfile, name='sender_profile')
        sendee_profile = aliased(UserProfile, name='sendee_profile')
        sender_account = aliased(Account, name='sender_account')
        sendee_account = aliased(Account, name='sendee_account')

        query = query.join(
            sender, Contact.sent_by == sender.row_id).\
            join(sender_account, sender.account_id == sender_account.row_id).\
            join(sender_profile, sender_profile.user_id == sender.row_id).\
            join(sendee, Contact.sent_to == sendee.row_id).\
            join(sendee_account, sendee.account_id == sendee_account.row_id).\
            join(sendee_profile, sendee_profile.user_id == sendee.row_id).\
            filter(or_(
                or_(
                    and_((func.concat(
                        func.lower(sender_profile.first_name),
                        ' ',
                        func.lower(sender_profile.last_name)).like(full_name)),
                        sender_profile.user_id != user_id)),
                and_((func.concat(
                    func.lower(sendee_profile.first_name),
                    ' ',
                    func.lower(sendee_profile.last_name)).like(full_name)),
                    sendee_profile.user_id != user_id)))
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/admin_contact_get_list.yml')
    def get(self):
        """
        Get the contact list
        """
        admin_contact_read_schema = AdminContactReadArgsSchema()
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            admin_contact_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(Contact), operator)
            # making a copy of the main output schema
            contact_schema = ContactSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                contact_schema = ContactSchema(only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = []
            for m in full_query.items:
                # also add the_other dynamic property
                if filters['user_id'] == m.sent_to:
                    m.the_other = m.sender
                else:
                    m.the_other = m.sendee
                models.append(m)
            total = full_query.total
            if not models:
                c_abort(404, message='No matching Contact found')
            result = contact_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
