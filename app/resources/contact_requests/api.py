"""
API endpoints for "contact requests" package.
"""

import datetime

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only, aliased
from sqlalchemy import func
from flasgger import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.resources.users.models import User
from app.resources.users import constants as USER
from app.resources.contact_requests.models import ContactRequest
from app.resources.contact_requests.schemas import (
    ContactRequestSchema, ContactRequestReadArgsSchema,
    ContactRequestEditSchema, ContactRequestHistorySchema)
from app.resources.contact_requests.helpers import (
    check_contact_request_exists, check_contact_exists,
    check_cross_contact_request)
from app.resources.contact_requests import constants as CONTACT
from app.resources.contacts.schemas import ContactSchema
from app.resources.notifications import constants as NOTIFY
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account
from app.resources.account_profiles.models import AccountProfile
from app.resources.notifications.models import Notification
from app.crm_resources.crm_contacts.models import CRMContact

from queueapp.notification_tasks import add_contact_request_notification
from queueapp.user_stats_tasks import manage_users_stats
from queueapp.feed_tasks import add_feed_for_new_contacts
from app.base import constants as APP


class ContactRequestAPI(AuthResource):
    """
    Create, update, delete API for contact
    """

    @swag_from('swagger_docs/contact_request_post.yml')
    def post(self):
        """
        Create a contact request
        """
        contact_request_schema = ContactRequestSchema()
        contact_schema = ContactSchema()

        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            # validate and deserialize input into object
            data, errors = contact_request_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            data.sent_by = g.current_user['row_id']

            # check cross contact request
            # if exists then create contact model automatically
            contact_request_data = check_cross_contact_request(data)
            if contact_request_data:
                contact_json_data = {}
                contact_json_data['sent_to'] = contact_request_data.sent_to
                contact_json_data['sent_by'] = contact_request_data.sent_by
                contact_data, errors = contact_schema.load(contact_json_data)
                if errors:
                    c_abort(422, errors=errors)
                contact_request_data.status = CONTACT.CRT_ACCEPTED
                contact_request_data.accepted_rejected_on = \
                    datetime.datetime.utcnow()
                db.session.add(contact_data)
                # deleting crm contact if exist
                CRMContact.query.filter(
                    CRMContact.created_by.in_(
                        (contact_data.sent_to, contact_data.sent_by)),
                    CRMContact.user_id.in_(
                        (contact_data.sent_to, contact_data.sent_by)
                    )
                ).delete(synchronize_session=False)
                db.session.add(contact_request_data)
                db.session.commit()
                # add feed for sender and sendee
                add_feed_for_new_contacts.s(True, contact_data.row_id).delay()
                # add notification for request sender
                add_contact_request_notification.s(
                    True, data.row_id, NOTIFY.NT_CONTACT_REQ_ACCEPTED).delay()
                # update user total_contact
                # for sent_to user
                manage_users_stats.s(
                    True, contact_data.sent_to, USER.USR_CONTS).delay()
                # for sent_by user
                manage_users_stats.s(
                    True, contact_data.sent_by, USER.USR_CONTS).delay()
                return {'message': 'Contact added %s' %
                        str(contact_data.row_id)}, 201

            # check if contact already exists
            errors = check_contact_exists(data)
            if errors:
                c_abort(422, errors={'sent_to': [errors]})

            # check if a "sent" or "accepted" contact request already exists
            errors = check_contact_request_exists(data)
            if errors:
                c_abort(422, errors={'sent_to': [errors]})

            # if all good, add data
            db.session.add(data)
            db.session.commit()
            add_contact_request_notification.s(
                True, data.row_id, NOTIFY.NT_CONTACT_REQ_RECEIVED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (sent_to)=(100) is not present in table "user".
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message='Sendee does not exist', errors={
                    column: ['Sendee does not exist']})
            # for any other unknown db errors
            current_app.logger.exception(e)
            abort(500)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Contact request added %s' % str(data.row_id),
                'row_id': data.row_id}, 201

    @swag_from('swagger_docs/contact_request_put.yml')
    def put(self, row_id):
        """
        Update a contact request status
        """
        contact_request_edit_schema = ContactRequestEditSchema()
        contact_schema = ContactSchema()
        model = None
        try:
            model = ContactRequest.query.get(row_id)
            if model is None:
                c_abort(404, message='ContactRequest id: %s does not exist' %
                                     str(row_id))
            # only sendee can change status of request
            if model.sent_to != g.current_user['row_id']:
                c_abort(401)
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)

        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)

        try:
            data, errors = contact_request_edit_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            if (data['status'] == CONTACT.CRT_ACCEPTED and
                    model.status == CONTACT.CRT_SENT or
                    model.status == CONTACT.CRT_ACCEPTED):
                contact_json_data = {}
                # check if contact already exists
                errors = check_contact_exists(model)
                if errors:
                    c_abort(422, errors={'sent_to': [errors]})
                contact_json_data['sent_to'] = model.sent_to
                contact_json_data['sent_by'] = model.sent_by
                contact_data, errors = contact_schema.load(
                    contact_json_data)
                if errors:
                    c_abort(422, errors={'sent_to': [errors]})
                model.status = data['status']
                model.accepted_rejected_on = datetime.datetime.utcnow()
                db.session.add(contact_data)
                # deleting crm contact if exist
                CRMContact.query.filter(
                    CRMContact.created_by.in_(
                        (contact_data.sent_to, contact_data.sent_by)),
                    CRMContact.user_id.in_(
                        (contact_data.sent_to, contact_data.sent_by)
                    )
                ).delete(synchronize_session=False)
                db.session.add(model)
                db.session.commit()
                # add feed for sender and sendee
                add_feed_for_new_contacts.s(True, contact_data.row_id).delay()
                # add notification for sender
                add_contact_request_notification.s(
                    True, row_id, NOTIFY.NT_CONTACT_REQ_ACCEPTED).delay()
                # manage user total_contact
                # for sent_to
                manage_users_stats.s(
                    True, contact_data.sent_to, USER.USR_CONTS).delay()
                # for sent_by
                manage_users_stats.s(
                    True, contact_data.sent_by, USER.USR_CONTS).delay()
            elif data['status'] == CONTACT.CRT_REJECTED:
                model.status = data['status']
                model.accepted_rejected_on = datetime.datetime.utcnow()
                db.session.add(model)
                db.session.commit()
                add_contact_request_notification.s(
                    True, row_id, NOTIFY.NT_CONTACT_REQ_REJECTED).delay()
            else:
                c_abort(422, errors={
                    'status': ['Contact request already rejected']})
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Contact Request %s' % str(data['status']),
                'row_id': row_id}, 200

    @swag_from('swagger_docs/contact_request_delete.yml')
    def delete(self, row_id):
        """
        Delete a contact request
        """
        contact_request_history_schema = ContactRequestHistorySchema()
        model = None
        try:
            model = ContactRequest.query.get(row_id)
            if model is None:
                c_abort(404, message='Contact Request id: %s does not exist' %
                                     str(row_id))
            if model.sent_by != g.current_user['row_id']:
                c_abort(401)
            # contact request notification delete
            notification = Notification.query.filter(
                Notification.contact_request_id == row_id).first()
            if notification:
                db.session.delete(notification)

            if model.status == CONTACT.CRT_SENT:
                contact_request_history = {}
                contact_request_history['sent_by'] = model.sent_by
                contact_request_history['sent_to'] = model.sent_to
                contact_request_history['status'] = model.status
                contact_request_history['accepted_rejected_on'] =\
                    model.accepted_rejected_on
                contact_history_data, errors = \
                    contact_request_history_schema.load(
                        contact_request_history)
                if errors:
                    c_abort(422, errors=errors)
                db.session.add(contact_history_data)
                db.session.delete(model)
                db.session.commit()
            else:
                c_abort(422, errors={'status': ['Not allowed to cancel']})
        except HTTPException as e:
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {'message': 'Contact Request deleted'}, 204

    @swag_from('swagger_docs/contact_request_get.yml')
    def get(self, row_id):
        """
        Get a contact request by id
        """
        contact_request_schema = ContactRequestSchema()
        try:
            # first find model
            model = ContactRequest.query.get(row_id)
            if model is None:
                c_abort(404, message='Contact Request id: %s'
                        ' does not exist' % str(row_id))
            result = contact_request_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class ContactRequestListAPI(AuthResource):
    """
    Read API for contact request lists, i.e, more than 1 contact request
    """
    model_class = ContactRequest

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['sender', 'sendee']
        super(ContactRequestListAPI, self).__init__(*args, **kwargs)

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
        full_name = None
        account_type = None
        sector_id = None
        industry_id = None
        # build specific extra queries filters
        # add extra filter for fetch contact requests either send or receive
        if extra_query:
            for f in extra_query:
                if 'sender_receiver' in extra_query and extra_query[
                        'sender_receiver']:
                    if extra_query['sender_receiver'] == CONTACT.CR_SRT_SEND:
                        query_filters['base'].append(
                            ContactRequest.sent_by == g.current_user['row_id'])
                    elif extra_query['sender_receiver'] == CONTACT.CR_SRT_RECV:
                        query_filters['base'].append(
                            ContactRequest.sent_to == g.current_user['row_id'])

                if 'account_type' in extra_query and extra_query[
                        'account_type']:
                    account_type = extra_query['account_type']

                if 'sector_id' in extra_query and extra_query['sector_id']:
                    sector_id = extra_query['sector_id']
                if 'industry_id' in extra_query and extra_query['industry_id']:
                    industry_id = extra_query['industry_id']

                if 'full_name' in extra_query and extra_query['full_name']:
                    full_name = '%' + (extra_query['full_name']).lower() + '%'

        if not full_name:
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
            ContactRequest, the_other_profile.first_name,
            the_other_profile.last_name, the_other_account.account_type,
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
        query_sent_to = query.join(
            sender, ContactRequest.sent_by == sender.row_id).\
            join(sender_account, sender.account_id == sender_account.row_id).\
            join(sender_profile, sender_profile.user_id == sender.row_id).\
            join(sender_account_profile,
                 sender_account_profile.account_id == sender_account.row_id).\
            join(sendee, ContactRequest.sent_to == sendee.row_id).\
            join(sendee_account, sendee.account_id == sendee_account.row_id).\
            join(sendee_profile, sendee_profile.user_id == sendee.row_id).\
            join(sendee_account_profile,
                 sendee_account_profile.account_id == sendee_account.row_id).\
            join(the_other, ContactRequest.sent_to == the_other.row_id).\
            join(the_other_account,
                 the_other.account_id == the_other_account.row_id).\
            join(the_other_profile,
                 the_other_profile.user_id == the_other.row_id).\
            join(
                the_other_account_profile,
                the_other_account_profile.account_id ==
                the_other_account.row_id).\
            filter(ContactRequest.sent_by == g.current_user['row_id'],
                   the_other_account.blocked==False)

        # query for contacts who has sent contact request
        query_sent_by = query_for_union.join(
            sender, ContactRequest.sent_by == sender.row_id).\
            join(sender_account, sender.account_id == sender_account.row_id).\
            join(sender_profile, sender_profile.user_id == sender.row_id).\
            join(sender_account_profile,
                 sender_account_profile.account_id == sender_account.row_id).\
            join(sendee, ContactRequest.sent_to == sendee.row_id).\
            join(sendee_account, sendee.account_id == sendee_account.row_id).\
            join(sendee_profile, sendee_profile.user_id == sendee.row_id).\
            join(sendee_account_profile,
                 sendee_account_profile.account_id == sendee_account.row_id).\
            join(the_other, ContactRequest.sent_by == the_other.row_id).\
            join(the_other_account,
                 the_other.account_id == the_other_account.row_id).\
            join(the_other_profile,
                 the_other_profile.user_id == the_other.row_id).\
            join(
                the_other_account_profile,
                the_other_account_profile.account_id ==
                the_other_account.row_id).\
            filter(ContactRequest.sent_to == g.current_user['row_id'],
                   the_other_account.blocked==False)

        query_main = query_sent_to.union(
            query_sent_by).order_by(
            the_other_profile.first_name).filter((func.concat(
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

        return query_main, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/contact_request_get_list.yml')
    def get(self):
        """
        Get the list
        """
        contact_request_read_schema = ContactRequestReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            contact_request_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(ContactRequest), operator)
            # making a copy of the main output schema
            contact_request_schema = ContactRequestSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                contact_request_schema = ContactRequestSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            # models = [m for m in full_query.items]
            for m in full_query.items:
                # also add the_other dynamic property
                if g.current_user['row_id'] == m[0].sent_to:
                    m[0].the_other = m[0].sender
                else:
                    m[0].the_other = m[0].sendee
                models.append(m[0])
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ContactRequest found')
            result = contact_request_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)

        return {'results': result.data, 'total': total}, 200
