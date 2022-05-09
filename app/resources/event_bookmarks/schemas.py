"""
Schemas for "event bookmarks" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.event_bookmarks.models import EventBookmark


class EventBookmarkSchema(ma.ModelSchema):
    """
    Schema for loading "event bookmark" from request,
    and also formatting output
    """

    class Meta:
        model = EventBookmark
        include_fk = True
        load_only = ('created_by', 'account_id')
        dump_only = default_exclude + ('created_by', 'account_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.eventbookmarkapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.eventbookmarklistapi')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    event = ma.Nested(
        'app.resources.events.schemas.EventSchema',
        exclude=['event_bookmarked'], dump_only=True)


class EventBookmarkReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "event bookmarks" filters from request args
    """
    event_id = fields.Integer()
    event_type = fields.String(load_only=True)
    # modified date fields
    start_date_from = fields.DateTime(load_only=True)
    start_date_to = fields.DateTime(load_only=True)
    end_date_from = fields.DateTime(load_only=True)
    end_date_to = fields.DateTime(load_only=True)
