"""
Schema for event calendars
"""

from marshmallow import fields

from app import ma
from app.base.schemas import BaseReadArgsSchema


class EventCalendarSchema(ma.Schema):
    """
    Schema for global activity
    """
    row_id = fields.Integer(dump_only=True)
    event_type = fields.String(dump_only=True)
    title = fields.String(dump_only=True)
    creator = fields.Integer(dump_only=True)
    account = fields.Integer(dump_only=True)
    name = fields.String(dump_only=True)
    account_name = fields.String(dump_only=True)
    account_type = fields.String(dump_only=True)
    description = fields.String(dump_only=True)
    invite_logo_url = fields.Url(dump_only=True)
    profile_thumbnail_url = fields.Url(dump_only=True)
    invited = fields.Integer(dump_only=True)
    hosted = fields.Integer(dump_only=True)
    collaborated = fields.Integer(dump_only=True)
    participated = fields.Integer(dump_only=True)
    start_date = fields.DateTime(dump_only=True)
    end_date = fields.DateTime(dump_only=True)
    invite_logo_filename = fields.String(dump_only=True)
    collaborated = fields.Integer(dump_only=True)
    profile_thumbnail = fields.String(dump_only=True)


class EventCalenderReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Event calendar" filters from request args
    """
    started_at = fields.Date(load_only=True)
    ended_at = fields.Date(load_only=True)
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)
