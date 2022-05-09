"""
Schemas for "user dashboard stats"
"""

from marshmallow import fields

from app import ma
from app.base.schemas import BaseReadArgsSchema


class UserDashboardStatsSchema(ma.Schema):
    """
    Schema for loading admin dashboard
    """
    total_events = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)
    total_count = fields.Integer(dump_only=True)


class UserDashboardStatsReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "user dashboard" filters from request args
    """

    # modified date fields
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)


class UserEventMonthWiseStatsSchema(ma.Schema):
    """
    Schema for loading user event month wise stats
    """

    month = fields.Integer(dump_only=True)
    count = fields.Integer(dump_only=True, missing=0)


class UserMonthWiseEventTypeStatsSchema(ma.Schema):
    """
        Schema for loading user event month wise stats
        """

    event_type_name = fields.String(dump_only=True)
    count = fields.Integer(dump_only=True, missing=0)
