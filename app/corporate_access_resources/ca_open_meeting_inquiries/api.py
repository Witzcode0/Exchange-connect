"""
API endpoints for "ca open meeting inquiries" package.
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
from app.corporate_access_resources.ca_open_meeting_inquiries.models \
    import CAOpenMeetingInquiry, CAOpenMeetingInquiryHistory
from app.corporate_access_resources.ca_open_meeting_inquiries.schemas \
    import (CAOpenMeetingInquirySchema,
            CAOpenMeetingInquiryReadArgsSchema,
            CAOpenMeetingInquiryHistorySchema)
from app.resources.user_profiles.models import UserProfile
from app.corporate_access_resources.corporate_access_event_inquiries import \
    constants as CA_EVENT_INQUIRY
from app.corporate_access_resources.ca_open_meetings.models import \
    CAOpenMeeting
from app.corporate_access_resources.ca_open_meeting_slots.models import \
    CAOpenMeetingSlot
from app.resources.users.models import User
from app.resources.notifications import constants as NOTIFY

from queueapp.ca_open_meetings.notification_tasks import (
    add_caom_slot_inquiry_generated_notification,
    add_caom_slot_inquiry_confirmed_notification)


class CAOpenMeetingInquiryAPI(AuthResource):
    """
    CRUD API for managing ca open meeting inquiry
    """
    @swag_from('swagger_docs/ca_open_meeting_inquiries_post.yml')
    def post(self):
        """
        Create a ca open meeting inquiry
        """
        ca_open_inquiries_schema = CAOpenMeetingInquirySchema()
        inquiries_history_schema = CAOpenMeetingInquiryHistorySchema()
        # get the json data from the request
        json_data = request.get_json()
        if not json_data:
            c_abort(400)
        inquiry_his_data = None
        try:
            # validate and deserialize input into object
            data, errors = ca_open_inquiries_schema.load(json_data)
            if errors:
                c_abort(422, errors=errors)

            slot_data = CAOpenMeetingSlot.query.get(
                data.ca_open_meeting_slot_id)
            # if event creator reject to particular user for particular slot
            inquiry_his_data = CAOpenMeetingInquiryHistory.query.filter(
                and_(CAOpenMeetingInquiryHistory.
                     ca_open_meeting_slot_id ==
                     data.ca_open_meeting_slot_id,
                     CAOpenMeetingInquiryHistory.status ==
                     CA_EVENT_INQUIRY.DELETED,
                     CAOpenMeetingInquiryHistory.created_by ==
                     g.current_user['row_id'],
                     CAOpenMeetingInquiryHistory.updated_by !=
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

            event_data = CAOpenMeeting.query.get(data.ca_open_meeting_id)
            # open meeting creator can not inquired
            if event_data.created_by == g.current_user['row_id']:
                c_abort(403)
            # if open meeting not open to all so only invitee can inquired
            if not event_data.open_to_all:
                invitee_user_id = [invitee.invitee_id for invitee in
                                   event_data.ca_open_meeting_invitees]
                if g.current_user['row_id'] not in invitee_user_id:
                    c_abort(403)

            if data.status == CA_EVENT_INQUIRY.CONFIRMED:
                c_abort(403)
            # for ca open meeting cancelled
            if event_data.cancelled:
                c_abort(422, errors='CA Open Meeting cancelled,'
                        ' so you cannot add an inquiry')

            # no errors, so add data to db
            data.created_by = g.current_user['row_id']
            data.updated_by = data.created_by
            db.session.add(data)
            db.session.commit()

            # data insert in history table
            his_data, errors = inquiries_history_schema.load(json_data)
            if not errors:
                his_data.created_by = g.current_user['row_id']
                his_data.updated_by = g.current_user['row_id']
                db.session.add(his_data)
                db.session.commit()

            # send notification to ca open meeting creator
            add_caom_slot_inquiry_generated_notification.s(
                True, data.row_id,
                NOTIFY.NT_CAOM_SLOT_INQUIRY_CREATED).delay()

        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_ALREADY_EXISTS in e.orig.diag.message_detail.lower():
                # Key (created_by, ca_open_meeting_id,
                # ca_open_meeting_slot_id)=(17, 16, 73) already exists.
                column = e.orig.diag.message_detail.split('(')[1][:-2]
                c_abort(422, message=APP.MSG_ALREADY_EXISTS, errors={
                    column: [APP.MSG_ALREADY_EXISTS]})
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (ca_open_meeting_id)=(3) is not present
                # in table "ca_open_meeting".
                # Key (ca_open_meeting_slot_id)=(10) is not present
                # in table "ca_open_meeting_slot".
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

        return {'message': 'CA Open Meeting Inquiry added: %s' %
                str(data.row_id), 'row_id': data.row_id}, 201

    @swag_from('swagger_docs/ca_open_meeting_inquiries_put.yml')
    def put(self, row_id):
        """
        Update a ca open meeting inquiry
        """
        ca_open_inquiries_schema = CAOpenMeetingInquirySchema()
        # first find model
        model = None
        model_status = None
        try:
            model = CAOpenMeetingInquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting '
                        'Inquiry id: %s does not exist' % str(row_id))

            # will be used for notifications
            model_status = model.status
            # if current user in disallow table for particular slot
            slot_data = CAOpenMeetingSlot.query.get(
                model.ca_open_meeting_slot_id)
            user_data = User.query.get(model.created_by)
            if slot_data.disallowed and user_data in slot_data.disallowed:
                c_abort(422, message='already confirmed slot',
                        errors={'status': ['already confirmed slot']})

            event_data = CAOpenMeeting.query.get(model.ca_open_meeting_id)
            # only event invitee can inquiry for particular slot
            invitee_user_id = [invitee.invitee_id for invitee in
                               event_data.ca_open_meeting_invitees]
            if (event_data.created_by != g.current_user['row_id'] and
                    g.current_user['row_id'] not in invitee_user_id):
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
            data, errors = ca_open_inquiries_schema.load(
                json_data, instance=model, partial=True)
            if errors:
                c_abort(422, errors=errors)
            # no errors, so add data to db
            # no permission to invitee to change confirm status
            if (event_data.created_by != g.current_user['row_id'] and
                    data.status == CA_EVENT_INQUIRY.CONFIRMED):
                c_abort(403)
            # for ca open meeting cancelled
            event = CAOpenMeeting.query.get(model.ca_open_meeting_id)
            if event.cancelled:
                c_abort(422, message='CA Open Meeting cancelled,'
                        ' so you cannot update an inquiry')

            if data.status == CA_EVENT_INQUIRY.CONFIRMED:
                # all inquiries for particular slot and creator
                slot_all_data = CAOpenMeetingSlot.query.filter(
                    CAOpenMeetingSlot.event_id ==
                    model.ca_open_meeting_id).all()

                if model_status != CA_EVENT_INQUIRY.CONFIRMED:
                    # if confirmed one slot so disallow to other slots
                    for slt in slot_all_data:
                        if model.ca_open_meeting_slot_id == slt.row_id:
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
            db.session.add(CAOpenMeetingInquiryHistory(
                ca_open_meeting_id=data.ca_open_meeting_id,
                ca_open_meeting_slot_id=data.ca_open_meeting_slot_id,
                status=data.status,
                created_by=data.created_by,
                updated_by=data.updated_by))
            db.session.commit()

            # if status is confirmed, send notification to the inquirer
            if (model_status == CA_EVENT_INQUIRY.INQUIRED and
                    data.status == CA_EVENT_INQUIRY.CONFIRMED):
                add_caom_slot_inquiry_confirmed_notification.s(
                    True, data.row_id,
                    NOTIFY.NT_CAOM_SLOT_INQUIRY_CONFIRMED).delay()
        except IntegrityError as e:
            db.session.rollback()
            if APP.DB_NOT_PRESENT in e.orig.diag.message_detail.lower():
                # format of the message:
                # Key (ca_open_meeting_id)=(3) is not present
                # in table "ca_open_meeting".
                # Key (ca_open_meeting_slot_id)=(10) is not present
                # in table "ca_open_meeting_slot".
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
        return {'message': 'Updated CA Open Meeting Inquiry id: %s' %
                str(row_id)}, 200

    @swag_from('swagger_docs/ca_open_meeting_inquiries_delete.yml')
    def delete(self, row_id):
        """
        Delete a ca open meeting inquiry
        """
        model = None
        try:
            # first find model
            model = CAOpenMeetingInquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting '
                        'Inquiry id: %s does not exist' % str(row_id))

            event_data = CAOpenMeeting.query.get(model.ca_open_meeting_id)
            if (event_data.created_by != g.current_user['row_id'] and
                    model.created_by != g.current_user['row_id']):
                c_abort(403)
            # for ca open meeting cancelled
            if event_data.cancelled:
                c_abort(422, message='CA Open Meeting cancelled,'
                        ' so you cannot delete an inquiry')

            # when delete confirmed inquiry so other slot allowed for
            # particular invitee
            user = User.query.filter_by(row_id=model.created_by).first()
            if model.status == CA_EVENT_INQUIRY.CONFIRMED:
                for slt in event_data.slots:
                    if slt.row_id == model.ca_open_meeting_slot_id:
                        if slt.booked_seats:
                            slt.booked_seats -= 1
                        db.session.add(slt)
                    if user in slt.disallowed:
                        slt.disallowed.remove(user)
            # insert into history data
            db.session.add(CAOpenMeetingInquiryHistory(
                ca_open_meeting_id=model.ca_open_meeting_id,
                ca_open_meeting_slot_id=model.ca_open_meeting_slot_id,
                status=CA_EVENT_INQUIRY.DELETED,
                created_by=model.created_by,
                updated_by=g.current_user['row_id']))

            db.session.delete(model)
            db.session.commit()
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

    @swag_from('swagger_docs/ca_open_meeting_inquiries_get.yml')
    def get(self, row_id):
        """
        Get a ca open meeting inquiry by id
        """
        ca_open_inquiries_schema = CAOpenMeetingInquirySchema()
        model = None
        try:
            # first find model
            model = CAOpenMeetingInquiry.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting '
                        'Inquiry id: %s does not exist' % str(row_id))
            result = ca_open_inquiries_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200


class CAOpenMeetingInquiryListAPI(AuthResource):
    """
    Read API for ca open meeting inquiry lists, i.e, more than 1 inquiry
    """
    model_class = CAOpenMeetingInquiry

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['creator', 'ca_open_meeting',
                                    'ca_open_meeting_slot']
        super(CAOpenMeetingInquiryListAPI, self).__init__(*args, **kwargs)

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
                full_name = '%' + (extra_query['full_name']).lower() + '%'

        query = self._build_final_query(query_filters, query_session, operator)

        if not main_filter or main_filter == CA_EVENT_INQUIRY.MNFT_MINE:
            query = query.filter(
                CAOpenMeetingInquiry.created_by == g.current_user['row_id'])
        elif main_filter == CA_EVENT_INQUIRY.MNFT_EVENT_CREATED:
            query = query.join(CAOpenMeeting, and_(
                CAOpenMeeting.row_id == CAOpenMeetingInquiry.
                ca_open_meeting_id,
                CAOpenMeeting.created_by == g.current_user['row_id']))
            if full_name:
                query = query.join(
                    UserProfile, UserProfile.user_id ==
                    CAOpenMeetingInquiry.created_by).filter((func.concat(
                        func.lower(UserProfile.first_name), ' ', func.lower(
                            UserProfile.last_name)).like(full_name)))
        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/ca_open_meeting_inquiries_get_list.yml')
    def get(self):
        """
        Get the list
        """
        ca_open_inquiries_read_schema = \
            CAOpenMeetingInquiryReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ca_open_inquiries_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(
                    filters, pfields, sort, pagination, db.session.query(
                        CAOpenMeetingInquiry), operator)
            # making a copy of the main output schema
            ca_open_inquiries_schema = CAOpenMeetingInquirySchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ca_open_inquiries_schema = CAOpenMeetingInquirySchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ca open meeting '
                        'inquiries found')
            result = ca_open_inquiries_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
