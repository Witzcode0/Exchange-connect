"""
Schemas for "ca open meeting inquiries" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_open_meeting_fields)
from app.corporate_access_resources.corporate_access_event_inquiries import (
    constants as CORPORATEACCESSEVENTINQUIRY)
from app.corporate_access_resources.ca_open_meeting_inquiries.models \
    import CAOpenMeetingInquiry, CAOpenMeetingInquiryHistory
from app.corporate_access_resources.ca_open_meeting_slots.models \
    import CAOpenMeetingSlot

# user details that will be passed while populating user relation
inquiry_user_fields = user_fields + ['email', 'profile.phone_number',
                                     'account.profile.profile_thumbnail_url']


class CAOpenMeetingInquirySchema(ma.ModelSchema):
    """
    Schema for loading "ca open meeting inquiries" from request,
    and also formatting output
    """
    status = field_for(
        CAOpenMeetingInquiry, 'status', validate=validate.OneOf(
            CORPORATEACCESSEVENTINQUIRY.CA_EVENT_INQUIRY_STATUS_TYPES))
    _cached_slot = None

    class Meta:
        model = CAOpenMeetingInquiry
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.caopenmeetinginquiryapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.caopenmeetinginquirylistapi')
    }, dump_only=True)

    ca_open_meeting = ma.Nested(
        'app.corporate_access_resources.'
        'ca_open_meetings.schemas.CAOpenMeetingSchema',
        only=ca_open_meeting_fields, dump_only=True)
    ca_open_meeting_slot = ma.Nested(
        'app.corporate_access_resources.'
        'ca_open_meeting_slots.schemas.CAOpenMeetingSlotSchema',
        dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=inquiry_user_fields,
        dump_only=True)

    @validates_schema(pass_original=True)
    def validate_event_slot_exists(self, data, original_data):
        """
        Validate particular slot exists for particular event
        """
        error = False
        slot = None
        if ('ca_open_meeting_slot_id' in original_data and
                original_data['ca_open_meeting_slot_id'] and
                'ca_open_meeting_id' in original_data and
                original_data['ca_open_meeting_id']):

            slot = CAOpenMeetingSlot.query.filter_by(
                event_id=original_data['ca_open_meeting_id']).all()
            if slot:
                slot_ids = [slt.row_id for slt in slot]
                if original_data['ca_open_meeting_slot_id'] not in slot_ids:
                    error = True

        if error:
            raise ValidationError(
                'Slot id:%(slot_id)s does not exist for event '
                'id:%(event_id)s' % {
                    'slot_id': original_data['ca_open_meeting_slot_id'],
                    'event_id': original_data['ca_open_meeting_id']},
                'ca_open_meeting_id,' 'ca_open_meeting_slot_id')

    @validates_schema(pass_original=True)
    def validate_available_slot_seats(self, data, original_data):
        """
        Validate available seat for particular slot
        """
        error = False
        slot_data = None
        if 'ca_open_meeting_slot_id' in original_data and \
                original_data['ca_open_meeting_slot_id']:
            slot_data = CAOpenMeetingSlot.query.get(
                original_data['ca_open_meeting_slot_id'])
            if ('status' in data and
                    original_data['status'] ==
                    CORPORATEACCESSEVENTINQUIRY.CONFIRMED and
                    slot_data.bookable_seats == slot_data.booked_seats):
                error = True
        self._cached_slot = slot_data
        if error:
            raise ValidationError('Seat not available for slot id %s' %
                                  slot_data.row_id,
                                  'ca_open_meeting_slot_id')


class CAOpenMeetingInquiryReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ca open meeting inquiries"
    filters from request args
    """
    ca_open_meeting_id = fields.Integer(load_only=True)
    ca_open_meeting_slot_id = fields.Integer(load_only=True)
    status = fields.String(load_only=True, validate=validate.OneOf(
        CORPORATEACCESSEVENTINQUIRY.CA_EVENT_INQUIRY_STATUS_TYPES))
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        CORPORATEACCESSEVENTINQUIRY.CA_INQUIRY_LISTS))
    full_name = fields.String(load_only=True)


class CAOpenMeetingInquiryHistorySchema(ma.ModelSchema):
    """
    Schema for loading "ca open meeting inquiries" from request,
    and also formatting output
    """
    status = field_for(
        CAOpenMeetingInquiry, 'status', validate=validate.OneOf(
            CORPORATEACCESSEVENTINQUIRY.CA_HIS_EVENT_INQUIRY_STATUS_TYPES))

    class Meta:
        model = CAOpenMeetingInquiryHistory
        include_fk = True
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.caopenmeetinginquiryhisapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.caopenmeetinginquiryhislistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=inquiry_user_fields,
        dump_only=True)
