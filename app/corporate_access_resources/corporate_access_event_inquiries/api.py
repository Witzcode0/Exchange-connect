"""
API endpoints for "corporate access event inquiries" package.
"""

from werkzeug.exceptions import Forbidden, HTTPException
from flask import request, current_app, g
from flask_restful import abort
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import load_only
from sqlalchemy import and_, func
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_inquiries.models \
    import CorporateAccessEventInquiry, CorporateAccessEventInquiryHistory
from app.corporate_access_resources.corporate_access_event_inquiries.schemas \
    import (CorporateAccessEventInquirySchema,
            CorporateAccessEventInquiryReadArgsSchema,
            CorporateAccessEventInquiryHistorySchema)
from app.resources.user_profiles.models import UserProfile
from app.corporate_access_resources.corporate_access_event_inquiries import \
    constants as CA_EVENT_INQUIRY
from app.corporate_access_resources.corporate_access_events.models import \
    CorporateAccessEvent
from app.corporate_access_resources.corporate_access_event_slots.models \
    import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_attendees.models \
    import CorporateAccessEventAttendee
from app.resources.accounts import constants as ACCOUNT
from app.resources.users.models import User

from queueapp.corporate_accesses.stats_tasks import (
    update_corporate_event_stats)
from queueapp.corporate_accesses.email_tasks import (
    # send_corporate_access_event_slot_inquiry_generated_email,
    send_corporate_access_event_slot_inquiry_confirmation_email,
    send_corporate_access_event_slot_inquiry_deletion_email)


class CorporateAccessEventInquiryAPI(AuthResource):
    """
    CRUD API for managing Corporate Access Event inquiry
    """
    @swag_from('swagger_docs/corporate_access_event_inquiries_post.yml')
    def post(self):
        """
        Create a Corporate Access Event inquiry
        """
        corporate_inquiries_schema = CorporateAccessEventInquirySchema()
        inquiries_history_schema = CorporateAccessEventInquiryHistorySchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        invitee_guest_emails = None
        inquiry_his_data = None
        try:
            # validate and deserialize input into object
            data, errors = corporate_inquiries_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            slot_data = CorporateAccessEventSlot.query.get(
                data.corporate_access_event_slot_id)
            # if event creator reject to particular user for particular slot
            inquiry_his_data = CorporateAccessEventInquiryHistory.query.filter(
                and_(CorporateAccessEventInquiryHistory.
                     corporate_access_event_slot_id ==
                     data.corporate_access_event_slot_id,
                     CorporateAccessEventInquiryHistory.status ==
                     CA_EVENT_INQUIRY.DELETED,
                     CorporateAccessEventInquiryHistory.created_by ==
                     g.current_user['row_id'],
                     CorporateAccessEventInquiryHistory.updated_by !=
                     g.current_user['row_id'])).first()
            if inquiry_his_data:
                c_abort(422, message='already rejected by event creator',
                        errors={'status': ['already rejected by event creator']
                                })
            # if current user in disallow table for particular slot
            user_data = User.query.get(g.current_user['row_id'])
            if (slot_data.disallowed and
                    user_data in slot_data.disallowed):
                c_abort(422, message='already confirmed slot',
                        errors={'status':
                                ['already confirmed slot']})

            event_data = CorporateAccessEvent.query.get(
                data.corporate_access_event_id)
            # only event invitee can inquiry for particular slot
            invitee_user_id = [invitee.invitee_id for invitee in
                               event_data.corporate_access_event_invitees]
            invitee_guest_emails = [invitee.invitee_email for invitee in
                                    event_data.corporate_access_event_invitees]
            if (g.current_user['row_id'] not in invitee_user_id and
                    g.current_user['account_type'] != ACCOUNT.ACCT_GUEST and
                    g.current_user['email'] not in invitee_guest_emails):
                c_abort(403)

            if data.status == CA_EVENT_INQUIRY.CONFIRMED:
                c_abort(403)
            # for cancelled event
            if event_data.cancelled:
                c_abort(422, errors='Corporate Access Event cancelled,'
                        ' so you cannot add an inquiry')

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by

            # uncomment the following variables once you
            # enable generated email task

            # cae and inquirer, to be used for sending email task
            # cae = data.corporate_access_event_id
            # inquirer = data.created_by
            # cae_slot = data.corporate_access_event_slot_id

            db.session.add(data)
            db.session.commit()

            # data insert in history table
            his_data, errors = inquiries_history_schema.load(json_data)
            if not errors:
                his_data.created_by = g.current_user['row_id']
                his_data.updated_by = g.current_user['row_id']
                db.session.add(his_data)
                db.session.commit()
            # if all ok then call task for stats calculation
            update_corporate_event_stats.s(
                True, data.corporate_access_event_id).delay()

            # currently unused, recheck before re-enabling

            # send emails to inquirer, creator, collaborator for the
            # slot inquiry generated
            # send_corporate_access_event_slot_inquiry_generated_email.s(
            #     True, cae_slot, cae, inquirer).delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # Key (created_by, corporate_access_event_id,
                # corporate_access_event_slot_id)=(17, 16, 73) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present
                # in table "corporate_access_event".
                # Key (corporate_access_event_slot_id)=(10) is not present
                # in table "corporate_access_event_slot".
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

        return {'message': 'Corporate Access Event Inquiry added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/corporate_access_event_inquiries_put.yml')
    def put(self, row_id):
        """
        Update a Corporate Access Event inquiry
        """
        corporate_inquiries_schema = CorporateAccessEventInquirySchema()
        # first find model
        model = None
        model_status = None
        try:
            model = CorporateAccessEventInquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'Inquiry id: %s does not exist' % str(row_id))

            # if current user in disallow table for particular slot
            slot_data = CorporateAccessEventSlot.query.get(
                model.corporate_access_event_slot_id)
            user_data = User.query.get(model.created_by)
            if (slot_data.disallowed and
                    user_data in slot_data.disallowed):
                c_abort(422, message='already confirmed slot',
                        errors={'status':
                                ['already confirmed slot']})
            # model_status and inquirer, to be used for email tasks
            model_status = model.status
            inquirer = model.created_by
            # old_corporate_access_event_id, to be used for stats_calculation
            # and email_tasks
            ce_id = model.corporate_access_event_id
            cae_slot = model.corporate_access_event_slot_id

            event_data = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            # only event invitee can inquiry for particular slot
            invitee_user_id = [invitee.invitee_id for invitee in
                               event_data.corporate_access_event_invitees]
            invitee_guest_emails = [invitee.invitee_email for invitee in
                                    event_data.corporate_access_event_invitees]
            collaborator_ids = [
                event.collaborator_id for event in event_data.collaborators]
            if (event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in collaborator_ids and
                    g.current_user['row_id'] not in invitee_user_id and
                    g.current_user['account_type'] != ACCOUNT.ACCT_GUEST and
                    g.current_user['email'] not in invitee_guest_emails):
                c_abort(403)

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
            data, errors = corporate_inquiries_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            # no permission to invitee to change confirm status
            if (event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in collaborator_ids and
                    data.status == CA_EVENT_INQUIRY.CONFIRMED):
                c_abort(403)
            # for cancelled event
            event = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            if event.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        ' so you cannot update an inquiry')

            if data.status == CA_EVENT_INQUIRY.CONFIRMED:
                # all inquiries for particular slot and creator
                slot_all_data = CorporateAccessEventSlot.query.filter(
                    CorporateAccessEventSlot.event_id ==
                    model.corporate_access_event_id).all()

                if model_status != CA_EVENT_INQUIRY.CONFIRMED:
                    # if confirmed one slot so disallow to other slots
                    for slt in slot_all_data:
                        if model.corporate_access_event_slot_id == slt.row_id:
                            slt.booked_seats += 1
                        else:
                            user_data = User.query.filter_by(
                                row_id=model.created_by).first()
                            slt.disallowed.append(user_data)
                        db.session.add(slt)
            data.updated_by = g.current_user['row_id']
            db.session.add(data)
            db.session.commit()
            # insert into history data
            db.session.add(CorporateAccessEventInquiryHistory(
                corporate_access_event_id=data.corporate_access_event_id,
                corporate_access_event_slot_id=data.
                corporate_access_event_slot_id,
                status=data.status,
                created_by=data.created_by,
                updated_by=data.updated_by))
            db.session.commit()
            # old_corporate_access_event_id, to be used for stats calculation
            if ce_id != model.corporate_access_event_id:
                update_corporate_event_stats.s(
                    True, model.corporate_access_event_id).delay()
            update_corporate_event_stats.s(True, ce_id).delay()
            # if status is confirmed, send emails
            if (model_status == CA_EVENT_INQUIRY.INQUIRED and
                    data.status == CA_EVENT_INQUIRY.CONFIRMED):
                send_corporate_access_event_slot_inquiry_confirmation_email.s(
                    True, cae_slot, ce_id, inquirer).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (corporate_access_event_id)=(3) is not present
                # in table "corporate_access_event".
                # Key (corporate_access_event_slot_id)=(10) is not present
                # in table "corporate_access_event_slot".
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
        return {'message': 'Updated Corporate Access Event Inquiry id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/corporate_access_event_inquiries_delete.yml')
    def delete(self, row_id):
        """
        Delete a Corporate Access Event inquiry
        """
        model = None
        try:
            # first find model
            model = CorporateAccessEventInquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'Inquiry id: %s does not exist' % str(row_id))

            event_data = CorporateAccessEvent.query.get(
                model.corporate_access_event_id)
            # model_status, to be used for sending emails
            model_status = model.status

            # collaborator details
            collaborator_ids = [
                event.collaborator_id for event in event_data.collaborators]
            if (event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in collaborator_ids and
                    model.created_by != g.current_user['row_id']):
                c_abort(403)
            # for cancelled event
            if event_data.cancelled:
                c_abort(422, message='Corporate Access Event cancelled,'
                        ' so you cannot delete an inquiry')

            # if user already attend particular event, so no delete permission
            if CorporateAccessEventAttendee.query.filter(and_(
                    CorporateAccessEventAttendee.
                    corporate_access_event_slot_id ==
                    model.corporate_access_event_slot_id,
                    CorporateAccessEventAttendee.attendee_id ==
                    model.created_by)).first():
                c_abort(422, message='User already attend event',
                        errors={'corporate_access_event_slot_id':
                                'User already attend event'})
            # when delete confirmed inquiry so other slot allowed for
            # particular invitee
            user = User.query.filter_by(row_id=model.created_by).first()
            if model.status == CA_EVENT_INQUIRY.CONFIRMED:
                for slt in event_data.slots:
                    if slt.row_id == model.corporate_access_event_slot_id:
                        if slt.booked_seats:
                            slt.booked_seats -= 1
                        db.session.add(slt)
                    if user in slt.disallowed:
                        slt.disallowed.remove(user)
            # insert into history data
            db.session.add(CorporateAccessEventInquiryHistory(
                corporate_access_event_id=model.corporate_access_event_id,
                corporate_access_event_slot_id=model.
                corporate_access_event_slot_id,
                status=CA_EVENT_INQUIRY.DELETED,
                created_by=model.created_by,
                updated_by=g.current_user['row_id']))

            # creator details
            creator_email = event_data.creator.email
            creator_name = event_data.creator.profile.first_name
            # inquirer details
            inquirer = model.created_by

            ce_id = model.corporate_access_event_id
            db.session.delete(model)
            db.session.commit()
            # old_corporate_access_event_id, to be used for stats calculation
            update_corporate_event_stats.s(True, ce_id).delay()
            # if confirmed inquiry deleted, send emails
            if model_status == CA_EVENT_INQUIRY.CONFIRMED:
                send_corporate_access_event_slot_inquiry_deletion_email.s(
                    True, ce_id, creator_email, creator_name, collaborator_ids,
                    inquirer).delay()
        except Forbidden as e:
            db.session.rollback()
            raise e
        except HTTPException as e:
            db.session.rollback()
            raise e
        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(e)
            abort(500)
        return {}, 204

    @swag_from('swagger_docs/corporate_access_event_inquiries_get.yml')
    def get(self, row_id):
        """
        Get a Corporate Access Event inquiry by id
        """
        corporate_inquiries_schema = CorporateAccessEventInquirySchema()
        model = None
        try:
            # first find model
            model = CorporateAccessEventInquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='Corporate Access Event '
                        'Inquiry id: %s does not exist' % str(row_id))
            result = corporate_inquiries_schema.dump(model)
        except Forbidden as e:
            raise e
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CorporateAccessEventInquiryListAPI(AuthResource):
    """
    Read API for corporate access event inquiry lists, i.e, more than 1
    """
    model_class = CorporateAccessEventInquiry

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'corporate_access_event',
                                    'corporate_access_event_slot']
        super(CorporateAccessEventInquiryListAPI, self).__init__(
            *args, **kwargs)

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
        main_filter = None
        full_name = ""
        if extra_query:
            if 'main_filter' in extra_query and extra_query['main_filter']:
                main_filter = extra_query['main_filter']
            if 'full_name' in extra_query and extra_query['full_name']:
                full_name = '%' + (extra_query["full_name"]).lower() + '%'

        query = self._build_final_query(query_filters, query_session, operator)

        if not main_filter or main_filter == CA_EVENT_INQUIRY.MNFT_MINE:
            query = query.filter(
                CorporateAccessEventInquiry.created_by ==
                g.current_user['row_id'])
        elif main_filter == CA_EVENT_INQUIRY.MNFT_EVENT_CREATED:
            query = query.join(CorporateAccessEvent, and_(
                CorporateAccessEvent.row_id == CorporateAccessEventInquiry.
                corporate_access_event_id,
                CorporateAccessEvent.created_by == g.current_user['row_id']))
            if full_name:
                query = query.join(
                    UserProfile, UserProfile.user_id ==
                    CorporateAccessEventInquiry.created_by).filter((
                        func.concat(func.lower(
                            UserProfile.first_name), ' ',
                            func.lower(UserProfile.last_name)).like(full_name)
                    ))
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/corporate_access_event_inquiries_get_list.yml')
    def get(self):
        """
        Get the list
        """
        corporate_inquiries_read_schema = \
            CorporateAccessEventInquiryReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            corporate_inquiries_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CorporateAccessEventInquiry), operator)
            # making a copy of the main output schema
            corporate_inquiries_schema = CorporateAccessEventInquirySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                corporate_inquiries_schema = CorporateAccessEventInquirySchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching corporate access '
                        'inquiry types found')
            result = corporate_inquiries_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
