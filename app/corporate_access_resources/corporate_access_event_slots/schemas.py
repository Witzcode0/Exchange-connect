"""
Schemas for "corporate access event slots" related models
"""

from flask import g
from marshmallow import (fields, validate, pre_dump, validates_schema,
                         ValidationError)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (default_exclude, BaseReadArgsSchema, user_fields,
                              account_fields, ca_event_fields)
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_slots.models \
    import CorporateAccessEventSlot
from app.corporate_access_resources.corporate_access_event_slots import \
    constants as CORPACCESSEVENTSLOT

# corporate event filelds
cor_acc_event_fields = ca_event_fields + ['creator']


class CorporateAccessEventSlotSchema(ma.ModelSchema):
    """
    Schema for loading "corporate access event slots" from request,
    and also formatting output
    """

    slot_type = field_for(
        CorporateAccessEventSlot, 'slot_type',
        validate=validate.OneOf(CORPACCESSEVENTSLOT.CA_EVENT_SLOT_TYPES))

    address = field_for(
        CorporateAccessEventSlot, 'address',
        validate=[validate.Length(max=CORPACCESSEVENTSLOT.ADDRESS_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    slot_name = field_for(
        CorporateAccessEventSlot, 'slot_name',
        validate=[validate.Length(max=CORPACCESSEVENTSLOT.SLOT_NAME_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])
    description = field_for(
        CorporateAccessEventSlot, 'description',
        validate=[validate.Length(
            max=CORPACCESSEVENTSLOT.DESCRIPTION_NAME_MAX_LENGTH,
            error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = CorporateAccessEventSlot
        include_fk = True
        load_only = ('created_by', 'updated_by', 'account_id')
        dump_only = default_exclude + ('created_by', 'updated_by',
                                       'account_id')
        exclude = ('inquiry_histories',)
    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('corporate_access_api.corporateaccesseventslotapi',
                          row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventslotlistapi')
    }, dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=cor_acc_event_fields, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    inquired = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=['row_id', 'email'],
        dump_only=True)

    corporate_access_event_inquiries = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_inquiries.'
        'schemas.CorporateAccessEventInquirySchema',
        only=['row_id', 'status', 'creator', 'attended'],
        dump_only=True))

    inquiry_histories = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_inquiries.'
        'schemas.CorporateAccessEventInquiryHistorySchema', only=[
            'status', 'corporate_access_event_slot_id', 'created_by',
            'updated_by', 'creator'], dump_only=True))
    # for invitee
    rejected = ma.Nested(
        'app.corporate_access_resources.corporate_access_event_inquiries.'
        'schemas.CorporateAccessEventInquiryHistorySchema', only=[
            'status', 'corporate_access_event_slot_id', 'created_by',
            'updated_by'], dump_only=True)
    # for event creator
    rejected_inquiries = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_inquiries.'
        'schemas.CorporateAccessEventInquiryHistorySchema', only=[
            'status', 'corporate_access_event_slot_id', 'creator'],
        dump_only=True))
    available_seats = fields.Integer(dump_only=True)

    @pre_dump(pass_many=True)
    def load_rejected_slots_and_available_seat(self, objs, many):
        """
        Loads available seat for particular slot
        """

        if many:
            for obj in objs:
                obj.available_seats = obj.bookable_seats - obj.booked_seats
                if obj.corporate_access_event_inquiries:
                    for inq in obj.corporate_access_event_inquiries:
                        if inq.creator.row_id == g.current_user['row_id']:
                            obj.inquired = inq.creator
                if obj.inquiry_histories:
                    inq_reject_list = []
                    for inq in obj.inquiry_histories:
                        # for event creator all rejected user
                        # for particular slot
                        if (obj.corporate_access_event.creator.row_id ==
                                g.current_user['row_id'] and
                                inq.updated_by == g.current_user['row_id'] and
                                inq.created_by != g.current_user['row_id']):
                            inq_reject_list.append(inq)
                        # for invitee whose rejected from event creator
                        # for particular slot
                        if (inq.updated_by != g.current_user['row_id'] and
                                inq.created_by == g.current_user['row_id']):
                            obj.rejected = inq
                            break
                    if inq_reject_list:
                        obj.rejected_inquiries = inq_reject_list
        else:
            objs.available_seats = objs.bookable_seats - objs.booked_seats
            if objs.corporate_access_event_inquiries:
                for inq in objs.corporate_access_event_inquiries:
                    if inq.creator.row_id == g.current_user['row_id']:
                        objs.inquired = inq.creator
            if objs.inquiry_histories:
                inq_reject_list = []
                for inq in objs.inquiry_histories:
                    # for event creator all rejected user
                    # for particular slot
                    if (objs.corporate_access_event.creator.row_id ==
                            g.current_user['row_id'] and
                            inq.updated_by == g.current_user['row_id'] and
                            inq.created_by != g.current_user['row_id']):
                        inq_reject_list.append(inq)
                    # for invitee whose rejected from event creator
                    # for particular slot
                    if (inq.updated_by != g.current_user['row_id'] and
                            inq.created_by == g.current_user['row_id']):
                        objs.rejected = inq
                        break

                if inq_reject_list:
                    objs.rejected_inquiries = inq_reject_list

    @validates_schema
    def validate_started_at_and_ended_at(self, data):
        """
        Validate started_at and ended_at(ended_at greater then started_at)
        """
        error = False
        if ('started_at' in data and data['started_at'] and
                'ended_at' not in data):
            raise ValidationError(
                'Please provide end date', 'ended_at')
        elif ('ended_at' in data and data['ended_at'] and
                'started_at' not in data):
            raise ValidationError(
                'Please provide start date', 'started_at')
        elif ('started_at' in data and data['started_at'] and
                'ended_at' in data and data['ended_at']):
            if data['started_at'] > data['ended_at']:
                error = True

        if error:
            raise ValidationError(
                'End date should be greater than Start date',
                'started_at, ended_at')

    @validates_schema(pass_original=True)
    def validate_slot_seats(self, data, original_data):
        """
        Validate when update bookable seat and bookable
        seats less then booked seats
        :param data:
        :return:
        """
        error = False
        booked_seats = None
        if ('bookable_seats' in original_data and original_data[
                'bookable_seats'] and
                'row_id' in original_data and original_data['row_id']):
            booked_seats = CorporateAccessEventSlot.query.filter_by(
                row_id=original_data['row_id']).first().booked_seats
            if booked_seats:
                if booked_seats > int(original_data['bookable_seats']):
                    error = True
        if error:
            raise ValidationError(
                '%s Booked seat(s). Bookable seats cannot be '
                'less than booked seats' % str(booked_seats), 'bookable_seats')


class CorporateAccessEventSlotReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate_access_event slots" filters from request args
    """

    account_id = fields.Integer(load_only=True)
    event_id = fields.Integer(load_only=True)
