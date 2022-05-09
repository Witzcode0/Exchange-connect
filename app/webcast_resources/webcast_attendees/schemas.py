"""
Schemas for "webcast attendees" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, webcast_fields)
from app.webcast_resources.webcast_attendees.models import (
    WebcastAttendee)


class WebcastAttendeeSchema(ma.ModelSchema):
    """
    Schema for loading "webcast attendees" from request,
    and also formatting output
    """

    class Meta:
        model = WebcastAttendee
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('webcast_api.webcastattendeeapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcastattendeelistapi')
    }, dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        only=webcast_fields, dump_only=True)

    attendee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class WebcastAttendeeEditSchema(WebcastAttendeeSchema):
    """
    Schema for loading "webcast edit attendees" from request,
    and also formatting output
    """

    class Meta:
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'attendee_id')


class WebcastAttendeeReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast attendees" filters from request args
    """
    attendee_id = fields.Integer(load_only=True)
    webcast_id = fields.Integer(load_only=True)
    rating = fields.Integer(load_only=True)
