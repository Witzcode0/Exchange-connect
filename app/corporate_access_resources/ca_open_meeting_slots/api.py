"""
API endpoints for "ca open meetings slots" package.
"""

from werkzeug.exceptions import HTTPException, Forbidden
from flask import current_app, g
from flask_restful import abort
from sqlalchemy.orm import load_only
from flasgger.utils import swag_from

from app import db, c_abort
from app.base.api import AuthResource
from app.corporate_access_resources.ca_open_meetings.models import \
    CAOpenMeeting
from app.corporate_access_resources.ca_open_meeting_slots.models \
    import CAOpenMeetingSlot
from app.corporate_access_resources.corporate_access_event_inquiries \
    import constants as INQUIRIES
from app.corporate_access_resources.ca_open_meeting_slots.schemas \
    import (CAOpenMeetingSlotSchema, CAOpenMeetingSlotReadArgsSchema)
from app.corporate_access_resources.ca_open_meeting_inquiries.models \
    import CAOpenMeetingInquiry, CAOpenMeetingInquiryHistory
from app.resources.notifications import constants as NOTIFY
from app.resources.users.models import User

from queueapp.ca_open_meetings.notification_tasks import \
    add_caom_slot_deleted_notification


class CAOpenMeetingSlotAPI(AuthResource):
    """
    Get API for ca open meeting slots
    """
    @swag_from('swagger_docs/ca_open_meeting_slots_get.yml')
    def get(self, row_id):
        """
        Get a ca open meeting slot by id
        """
        ca_open_slot_schema = CAOpenMeetingSlotSchema()
        model = None
        try:
            # first find model
            model = CAOpenMeetingSlot.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting Slot id: %s'
                        ' does not exist' % str(row_id))
            result = ca_open_slot_schema.dump(model)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result}, 200

    @swag_from('swagger_docs/ca_open_meeting_slots_delete.yml')
    def delete(self, row_id):
        """
        Delete a ca open meeting slot
        """
        model = None
        try:
            # first find model
            model = CAOpenMeetingSlot.query.get(row_id)
            if model is None:
                c_abort(404, message='CA Open Meeting Slot id: %s'
                        ' does not exist' % str(row_id))

            # ownership check
            # for group account type user check with account id for
            # child account
            if (model.created_by != g.current_user['row_id'] or
                    model.account_id != g.current_user['account_id']):
                c_abort(403)
            # for ca open meeting cancelled
            event_data = CAOpenMeeting.query.get(model.event_id)
            if event_data.cancelled:
                c_abort(422, message='CA Open Meeting cancelled,'
                        ' so you cannot delete a slot')
            # caom and caom_slot_name, to be used for notifications
            caom_id = model.event_id
            caom_slot_name = ''
            if model.slot_name:
                caom_slot_name = model.slot_name

            # slot inquirers details
            slot_inquirers = CAOpenMeetingInquiry.query.filter_by(
                ca_open_meeting_id=caom_id,
                ca_open_meeting_slot_id=row_id,
                status=INQUIRIES.CONFIRMED).all()
            slot_inquirer_user_ids = [si.created_by for si in slot_inquirers]
            # if slot delete any confirmed inquired can be inquiry for
            # another slots
            for slot in CAOpenMeetingSlot.query.filter_by(
                    event_id=caom_id).all():
                if slot.row_id != row_id:
                    for user_id in slot_inquirer_user_ids:
                        user_data = User.query.get(user_id)
                        if user_data in slot.disallowed:
                            slot.disallowed.remove(user_data)

            # send notifications to slot inquiry confirmed users
            add_caom_slot_deleted_notification.s(
                True, caom_id, caom_slot_name,
                slot_inquirer_user_ids,
                NOTIFY.NT_CAOM_SLOT_DELETED).delay()
            # when slot delete then delete it's related inquiry
            # and inquiry history delete
            CAOpenMeetingInquiry.query.filter(
                CAOpenMeetingInquiry.
                ca_open_meeting_slot_id == row_id).delete()
            CAOpenMeetingInquiryHistory.query.filter(
                CAOpenMeetingInquiryHistory.
                ca_open_meeting_slot_id == row_id).delete()
            db.session.delete(model)
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


class CAOpenMeetingSlotListAPI(AuthResource):
    """
    Read API for ca open meeting slot list, i.e, more than 1 slot
    """
    model_class = CAOpenMeetingSlot

    def __init__(self, *args, **kwargs):
        kwargs['special_fields'] = ['ca_open_meeting',
                                    'account', 'creator']
        super(CAOpenMeetingSlotListAPI, self).__init__(*args, **kwargs)

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

        query = self._build_final_query(query_filters, query_session, operator)

        return query, db_projection, s_projection, order, paging

    @swag_from('swagger_docs/ca_open_meeting_slots_get_list.yml')
    def get(self):
        """
        Get the list
        """
        ca_open_slot_read_schema = CAOpenMeetingSlotReadArgsSchema(strict=True)
        models = []
        total = 0
        # parse the request query arguments
        filters, pfields, sort, pagination, operator = self.parse_args(
            ca_open_slot_read_schema)
        try:
            # build the sql query
            query, db_projection, s_projection, order, paging =\
                self.build_query(filters, pfields, sort, pagination,
                                 db.session.query(CAOpenMeetingSlot),
                                 operator)
            # making a copy of the main output schema
            ca_open_slot_schema = CAOpenMeetingSlotSchema()
            if db_projection:
                # change the query to include only requested fields
                query = query.options(load_only(*db_projection))
            if s_projection:
                # change the schema to include only requested fields
                ca_open_slot_schema = CAOpenMeetingSlotSchema(
                    only=s_projection)
            # make query
            full_query = query.order_by(*order).paginate(
                paging['page'], paging['per_page'], error_out=False)
            # prepare models for output dump
            models = [m for m in full_query.items]
            total = full_query.total
            if not models:
                c_abort(404, message='No matching ca open meeting slots found')
            result = ca_open_slot_schema.dump(models, many=True)
        except HTTPException as e:
            raise e
        except Exception as e:
            current_app.logger.exception(e)
            abort(500)
        return {'results': result.data, 'total': total}, 200
