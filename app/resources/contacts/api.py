"""
API endpoints for "contacts" package.
"""

import datetime

from werkzeug.exceptions import HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import load_only, aliased
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from app.resources.users import constants as USER
from app.resources.contacts.models import Contact
from app.resources.contact_requests.models import ContactRequest
from app.resources.contact_requests.schemas import (
    ContactRequestHistorySchema, ContactRequestSchema)
from app.resources.contacts.schemas import (
    ContactHistorySchema, ContactReadArgsSchema, ContactSchema,
    ContactAddByQRCodeSchema)
from app.resources.contact_requests.helpers import (
    check_contact_request_exists)
from app.resources.contact_requests import constants as CONTACT
from app.resources.feeds.models import FeedItem
from app.resources.account_profiles.models import AccountProfile
from app.resources.notifications.models import Notification
from app.crm_resources.crm_groups.models import CRMGroup

from queueapp.user_stats_tasks import manage_users_stats
from queueapp.feed_tasks import add_feed_for_new_contacts


class ContactAPI(AuthResource):
    """
    Delete Contact
    """

    @swag_from('swagger_docs/contact_delete.yml')
    def delete(self, row_id):
        """
        Delete contact by sender
        :param row_id:
        :return:
        """
        contact_history_schema = ContactHistorySchema()
        model = None
        try:
            model = Contact.query.get(row_id)
            if model is None:
                c_abort(404, message='Contact id: %s does not exist' %
                                     str(row_id))
            if (model.sent_by == g.current_user['row_id'] or
                    model.sent_to == g.current_user['row_id']):
                contact_history = {}
                contact_history['sent_by'] = model.sent_by
                contact_history['sent_to'] = model.sent_to
                contact_history_data, errors = \
                    contact_history_schema.load(
                        contact_history)
                if errors:
                    c_abort(422, errors=errors)
                # delete user from all crm group which is created by current
                # user
                crm_contact_user = None
                if g.current_user['row_id'] == model.sent_by:
                    crm_contact_user = model.sendee
                else:
                    crm_contact_user = model.sender

                groups = CRMGroup.query.filter(
                    CRMGroup.created_by == g.current_user['row_id']).all()
                for group in groups:
                    if crm_contact_user in group.group_contacts:
                        group.group_contacts.remove(crm_contact_user)
                    db.session.add(group)
                FeedItem.query.filter(or_(
                    and_(FeedItem.user_id == model.sent_by,
                         FeedItem.poster_id == model.sent_to),
                    and_(FeedItem.user_id == model.sent_to,
                         FeedItem.poster_id == model.sent_by))).delete()
                db.session.commit()

                db.session.add(contact_history_data)
                db.session.delete(model)

                # delete contact request
                cont_req_data = ContactRequest.query.filter(or_(
                    and_(
                        ContactRequest.sent_by == model.sent_by,
                        ContactRequest.sent_to == model.sent_to),
                    and_(
                        ContactRequest.sent_to == model.sent_by,
                        ContactRequest.sent_by == model.sent_to))).all()
                # contact request notification delete
                for cont_req in cont_req_data:
                    notification = Notification.query.filter(
                        Notification.contact_request_id ==
                        cont_req.row_id).delete(synchronize_session=False)

                if cont_req_data:
                    for cont_req in cont_req_data:
                        contact_request_history = {}
                        contact_request_history['sent_by'] = cont_req.sent_by
                        contact_request_history['sent_to'] = cont_req.sent_to
                        contact_request_history['status'] = cont_req.status
                        contact_history_data, errors = \
                            ContactRequestHistorySchema().load(
                                contact_request_history)
                        if errors:
                            c_abort(422, errors=errors)
                        contact_history_data.accepted_rejected_on = \
                            cont_req.accepted_rejected_on
                        db.session.add(contact_history_data)
                        db.session.delete(cont_req)
                    db.session.commit()
                # for update user total_contact
                # for sent_to
                manage_users_stats.s(
                    True, model.sent_to, USER.USR_CONTS,
                    increase=False).delay()
                # for sent_by
                manage_users_stats.s(
                    True, model.sent_by, USER.USR_CONTS,
                    increase=False).delay()
            else:
                c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Contact deleted %s' %
                str(row_id)}, 204


class ContactListAPI(AuthResource):
    """
    Read API for contact lists, i.e, more than 1 contacts
    """
    model_class = Contact

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['sender', 'sendee', 'the_other']
        super(ContactListAPI, self).__init__(*args, **kwargs)

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
        account_type = None
        sector_id = None
        industry_id = None
        if extra_query:
            for f in extra_query:
                if "full_name" in extra_query and extra_query[
                        'full_name']:
                    full_name = '%' + (extra_query["full_name"]).lower() + '%'
                if "account_type" in extra_query and extra_query[
                        'account_type']:
                    account_type = extra_query['account_type']

                if 'sector_id' in extra_query and extra_query['sector_id']:
                    sector_id = extra_query['sector_id']
                if 'industry_id' in extra_query and extra_query['industry_id']:
                    industry_id = extra_query['industry_id']
        if full_name == "":
            full_name = '%%'

        # produce alias for user, user_profile, account and account_profile
        # tables so that we can use aliased object instead of main one
        # at different places for queries and filters.
        sender = aliased(User, name='sender')
        sendee = aliased(User, name='sendee')
        sender_profile = aliased(UserProfile, name='sender_profile')
        sendee_profile = aliased(UserProfile, name='sendee_profile')
        sender_account = aliased(Account, name='sender_account')
        sendee_account = aliased(Account, name='sendee_account')
        sendee_account_profile = aliased(
            AccountProfile, name='sendee_account_profile')
        sender_account_profile = aliased(
            AccountProfile, name='sender_account_profile')
        the_other = aliased(User, name='the_other')
        the_other_profile = aliased(UserProfile, name='the_other_profile')
        the_other_account = aliased(Account, name='the_other_account')
        the_other_account_profile = aliased(
            AccountProfile, name='the_other_account_profile')

        # added sector and industry to the_other_account_profile
        # in query_session to fetch by filters
        query_session = db.session.query(
            Contact, the_other_profile.first_name, the_other_profile.last_name,
            the_other_account.account_type,
            the_other_account_profile.sector_id,
            the_other_account_profile.industry_id)

        # append extra query filter to fetch contacts either send or receive
        query = self._build_final_query(query_filters, query_session, operator)
        query_for_union = self._build_final_query(
            query_filters, query_session, operator)
        # eager load account and user profile table
        # #TODO: improve by loading only required fields of user profile,
        # right now, if we load only required fields, it is making many queries

        # query for contacts who has received contact request
        query_sent_to = query.join(sender, Contact.sent_by == sender.row_id).\
            join(sender_account, sender.account_id == sender_account.row_id).\
            join(sender_profile, sender_profile.user_id == sender.row_id).\
            join(sender_account_profile,
                 sender_account_profile.account_id == sender_account.row_id).\
            join(sendee, Contact.sent_to == sendee.row_id).\
            join(sendee_account, sendee.account_id == sendee_account.row_id).\
            join(sendee_profile, sendee_profile.user_id == sendee.row_id).\
            join(sendee_account_profile,
                 sendee_account_profile.account_id == sendee_account.row_id).\
            join(the_other, Contact.sent_to == the_other.row_id).\
            join(the_other_account,
                 the_other.account_id == the_other_account.row_id).\
            join(the_other_profile,
                 the_other_profile.user_id == the_other.row_id).\
            join(
                the_other_account_profile,
                the_other_account_profile.account_id ==
                the_other_account.row_id).\
            filter(Contact.sent_by == g.current_user['row_id'],
                   the_other_account.blocked==False,
                   sender.deactivated.is_(False),
                   sendee.deactivated.is_(False))

        # query for contacts who has sent contact request
        query_sent_by = query_for_union.join(
            sender, Contact.sent_by == sender.row_id).\
            join(sender_account, sender.account_id == sender_account.row_id).\
            join(sender_profile, sender_profile.user_id == sender.row_id).\
            join(sender_account_profile,
                 sender_account_profile.account_id == sender_account.row_id).\
            join(sendee, Contact.sent_to == sendee.row_id).\
            join(sendee_account, sendee.account_id == sendee_account.row_id).\
            join(sendee_profile, sendee_profile.user_id == sendee.row_id).\
            join(sendee_account_profile,
                 sendee_account_profile.account_id == sendee_account.row_id).\
            join(the_other, Contact.sent_by == the_other.row_id).\
            join(the_other_account,
                 the_other.account_id == the_other_account.row_id).\
            join(the_other_profile,
                 the_other_profile.user_id == the_other.row_id).\
            join(
                the_other_account_profile,
                the_other_account_profile.account_id ==
                the_other_account.row_id).\
            filter(Contact.sent_to == g.current_user['row_id'],
                   the_other_account.blocked==False,
                   sender.deactivated.is_(False),
                   sendee.deactivated.is_(False))

        query_main = query_sent_to.union(
            query_sent_by).filter((func.concat(
                func.lower(the_other_profile.first_name),
                ' ',
                func.lower(the_other_profile.last_name)).like(full_name)))
        if account_type:
            query_main = query_main.filter(
                the_other_account.account_type == account_type)

        if sector_id:
            query_main = query_main.filter(
                the_other_account_profile.sector_id == sector_id)
        if industry_id:
            query_main = query_main.filter(
                the_other_account_profile.industry_id == industry_id)
        if sort:
            if 'first_name' in sort['sort_by']:
                query_main = query_main.order_by(the_other_profile.first_name)
            elif 'last_name' in sort['sort_by']:
                query_main = query_main.order_by(the_other_profile.last_name)

        return query_main, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/contact_get_list.yml')
    def get(self):
        """
        Get the contact list
        """
        contact_read_schema = ContactReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            contact_read_schema)
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
                if g.current_user['row_id'] == m[0].sent_to:
                    m[0].the_other = m[0].sender
                else:
                    m[0].the_other = m[0].sendee
                models.append(m[0])
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


class ContactAddByQRCodeAPI(AuthResource):
    """
    API for send contact add by QR code
    """

    @swag_from('swagger_docs/contact_addby_qrcode.yml')
    def post(self):
        """
        Create contact directly
        :return:
        """
        contact_request_schema = ContactRequestSchema()
        contact_add_by_qr_schema = ContactAddByQRCodeSchema()
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = contact_add_by_qr_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.sent_by = g.current_user['row_id']

            errors = check_contact_request_exists(data)
            if errors:
                c_abort(422, errors={'sent_to': [errors]})
            db.session.add(data)
            # add in contact request
            contact_request_json_data = {}
            contact_request_json_data['sent_to'] = data.sent_to
            contact_request_json_data['status'] = CONTACT.CRT_ACCEPTED
            contact_request_data, errors = contact_request_schema.load(
                contact_request_json_data)
            if errors:
                c_abort(422, errors=errors)
            contact_request_data.accepted_rejected_on = \
                datetime.datetime.utcnow()
            contact_request_data.sent_by = data.sent_by
            db.session.add(contact_request_data)
            db.session.commit()
            # add feed for sender and sendee
            add_feed_for_new_contacts.s(True, data.row_id).delay()
            # for sent_to user
            manage_users_stats.s(
                True, data.sent_to, USER.USR_CONTS).delay()
            # for sent_by user
            manage_users_stats.s(
                True, data.sent_by, USER.USR_CONTS).delay()
        except IntegrityError as e:
            # format of the message:
            # Key (sent_to)=(100) is not present in table "user".
            column = e.orig.diag.message_detail.split('(')[1][:-2]
            db.session.rollback()
            c_abort(422, message='Sendee does not exist', errors={
                column: ['Sendee does not exist']})
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Contact added %s' % str(data.row_id),
                'row_id': data.row_id}, 201
