"""
Schemas for "webinar attendees" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webinar_fields)
from app.webinar_resources.webinar_attendees.models import WebinarAttendee


class WebinarAttendeeSchema(ma.ModelSchema):
    """
    Schema for loading "webinar attendees" from request,
    and also formatting output
    """

    class Meta:
        model = WebinarAttendee
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webinar_api.webinarattendeeapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarattendeelistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)

    attendee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class WebinarAttendeeEditSchema(WebinarAttendeeSchema):
    """
    Schema for loading "webinar edit attendees" from request,
    and also formatting output
    """

    class Meta:
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'attendee_id')


class WebinarAttendeeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar attendees" filters from request args
    """
    attendee_id = fields.Integer(load_only=True)
    webinar_id = fields.Integer(load_only=True)
    rating = fields.Integer(load_only=True)
