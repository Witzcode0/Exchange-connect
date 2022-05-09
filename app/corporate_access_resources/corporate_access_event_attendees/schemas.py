"""
Schemas for "corporate access event attendees" related models
"""

from marshmallow import fields, validates_schema, ValidationError
from sqlalchemy import and_
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_event_fields)
from app.corporate_access_resources.corporate_access_event_attendees.models \
    import CorporateAccessEventAttendee
from app.corporate_access_resources.corporate_access_event_inquiries.models \
    import CorporateAccessEventInquiry
from app.corporate_access_resources.corporate_access_event_invitees.models \
    import CorporateAccessEventInvitee
from app.corporate_access_resources.corporate_access_event_inquiries import \
    constants as INQUIRY
from app.resources.users.models import User

attendee_ca_event_fields = ca_event_fields + ['stats.average_rating', 'cancelled']


class CorporateAccessEventAttendeeSchema(ma.ModelSchema):
    """
    Schema for loading "corporate access event attendees" from request,
    and also formatting output
    """

    class Meta:
        model = CorporateAccessEventAttendee
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')
        exclude = ('attendee_j', )

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.corporateaccesseventattendeeapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventattendeelistapi')
    }, dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=attendee_ca_event_fields, dump_only=True)
    corporate_access_event_slot = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_event_slots.schemas.CorporateAccessEventSlotSchema',
        dump_only=True)
    attendee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    guest_invitee = ma.List(ma.Nested(
        'app.corporate_access_resources.corporate_access_event_invitees.'
        'schemas.CorporateAccessEventInviteeSchema', only=[
            'row_id', 'invitee_email', 'invitee_first_name',
            'invitee_last_name', 'invitee_designation']), dump_only=True)

    @validates_schema(pass_original=True)
    def validate_event_slot_confirmation(self, data, original_data):
        """
        Validation for slot confirmation for particular attendee user
        """
        error = False
        inquiry_data = None
        if ('corporate_access_event_id' in original_data and
                original_data['corporate_access_event_id'] and
                'attendee_id' in original_data and
                original_data['attendee_id'] and
                'corporate_access_event_slot_id' in original_data and
                original_data['corporate_access_event_slot_id']):
            inquiry_data = CorporateAccessEventInquiry.query.filter(and_(
                CorporateAccessEventInquiry.corporate_access_event_id ==
                original_data['corporate_access_event_id'],
                CorporateAccessEventInquiry.corporate_access_event_slot_id ==
                original_data['corporate_access_event_slot_id'],
                CorporateAccessEventInquiry.created_by ==
                original_data['attendee_id'],
                CorporateAccessEventInquiry.status == INQUIRY.CONFIRMED)
            ).first()

            if not inquiry_data:
                error = True

        if error:
            raise ValidationError(
                'Slot id:%(slot_id)s not inquiry confirm for attendee id'
                ':%(attendee_id)s' % {'slot_id': original_data[
                                      'corporate_access_event_slot_id'],
                                      'attendee_id': original_data[
                                      'attendee_id']},
                'corporate_access_event_slot_id, attendee_id')

    @validates_schema(pass_original=True)
    def validate_event_invitee_exists(self, data, original_data):
        """
        Validate for event invitee exists or not
        """
        error = False
        invitee_data = None
        attendee_data = None
        # when attended id
        if ('corporate_access_event_id' in original_data and original_data[
                'corporate_access_event_id'] and 'attendee_id' in
                original_data and original_data['attendee_id'] and
                'corporate_access_event_slot_id' not in original_data):
            invitee_data = CorporateAccessEventInvitee.query.filter(and_(
                CorporateAccessEventInvitee.corporate_access_event_id ==
                original_data['corporate_access_event_id'],
                CorporateAccessEventInvitee.user_id == original_data[
                    'attendee_id'])).first()
            if not invitee_data:
                raise ValidationError(
                    'Attendee id: %s have no invitation' % original_data[
                        'attendee_id'], 'attendee_id')
        # when guest user use as a invitee_id
        elif ('corporate_access_event_id' in original_data and original_data[
                'corporate_access_event_id'] and 'invitee_id' in
                original_data and original_data['invitee_id'] and
                'corporate_access_event_slot_id' not in original_data):
            invitee_data = CorporateAccessEventInvitee.query.filter(
                CorporateAccessEventInvitee.row_id == original_data[
                    'invitee_id']).first()
            if not invitee_data:
                raise ValidationError(
                    'Invitee id: %s not exists' % str(original_data[
                        'invitee_id']), 'invitee_id')


class CorporateAccessEventAttendeeEditSchema(
        CorporateAccessEventAttendeeSchema):
    """
    Schema for loading "corporate access event edit attendees" from request,
    and also formatting output
    """

    class Meta:
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'attendee_id')


class CorporateAccessEventAttendeeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate access event attendees"
    filters from request args
    """
    attendee_id = fields.Integer(load_only=True)
    corporate_access_event_id = fields.Integer(load_only=True)
    corporate_access_event_slot_id = fields.Integer(load_only=True)
    rating = fields.Integer(load_only=True)
    cancelled = fields.Boolean(load_only=True)


class InquiriesSchema(ma.Schema):
    """
    Schema for inquiry
    """
    row_id = fields.Integer()
    inquiry_id = fields.Integer(required=True)
    comment = fields.String()

    @validates_schema(pass_original=True)
    def validate_event_slot_inquiry_ids(self, data, original_data):
        """
        Validate inquiry ids confirm for particular slot
        """
        error = False
        if 'inquiry_id' in original_data and original_data['inquiry_id']:
            inquiry_data = CorporateAccessEventInquiry.query.filter(and_(
                CorporateAccessEventInquiry.row_id ==
                original_data['inquiry_id'],
                CorporateAccessEventInquiry.status ==
                INQUIRY.CONFIRMED)).options(
                    load_only('row_id', 'created_by')).first()

            if not inquiry_data:
                error = True

        if error:
            raise ValidationError('Inquiry id: %s not confirmed' %
                                  original_data['inquiry_id'], 'inquiry_id')


class InviteeSchema(ma.Schema):
    """
    Schema for invitee
    """
    row_id = fields.Integer()
    invitee_id = fields.Integer()
    comment = fields.String()


class BulkCorporateAccessEventAttendeeSchema(ma.Schema):
    """
    Schema for bulk corporate access event attendee
    """
    inquiries = fields.List(fields.Nested(InquiriesSchema))
    corporate_access_event_slot_id = fields.Integer()
    invitees = fields.List(fields.Nested(InviteeSchema))

    @validates_schema(pass_original=True)
    def validate_invitees_and_inquiries(self, data, original_data):
        """
        Validate at a time only one used(inquiries and invitees)
        """
        error = False
        if ('inquiries' in original_data and original_data['inquiries'] and
                'invitees' in original_data and original_data['invitees']):
            error = True

        if error:
            raise ValidationError(
                'You can not use both at the same time', 'inquires, invitees')


class BulkCorporateAccessAttendeesSchema(ma.Schema):
    """
    Schema for bulk corporate access event attendees
    """
    corporate_access_event_id = fields.Integer(required=True)
    attendees = ma.List(ma.Nested(BulkCorporateAccessEventAttendeeSchema))
    attendee_delete_ids = fields.List(fields.Integer())
