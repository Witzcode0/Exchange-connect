"""
Schemas for "admin dashboard stats"
"""

from marshmallow import fields

from app import ma
from app.base.schemas import BaseReadArgsSchema


class TotalUserByTypeSchema(ma.Schema):
    active_user_count = fields.Integer(dump_only=True)
    deactivated_user_count = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class TotalAccountByTypeSchema(ma.Schema):
    active_account_count = fields.Integer(dump_only=True)
    deactivated_account_count = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class TotalWebinarByTypeSchema(ma.Schema):
    total_webinar_count = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class TotalWebcastByTypeSchema(ma.Schema):
    total_webcast_count = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class TotalProjectByTypeSchema(ma.Schema):
    total_project_count = fields.Integer(dump_only=True)
    project_type_name = fields.String(dump_only=True)


class TotalMeetingByTypeSchema(ma.Schema):
    total_meeting_count = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class TotalCAEventByTypeSchema(ma.Schema):
    total_ca_event_count = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class AdminDashboardStatsSchema(ma.Schema):
    """
    Schema for loading admin dashboard
    """
    total_users = fields.Integer(dump_only=True)
    total_active_users = fields.Integer(dump_only=True)
    total_deactive_users = fields.Integer(dump_only=True)
    total_accounts = fields.Integer(dump_only=True)
    total_active_accounts = fields.Integer(dump_only=True)
    total_deactive_accounts = fields.Integer(dump_only=True)
    total_webinars = fields.Integer(dump_only=True)
    total_webcasts = fields.Integer(dump_only=True)
    total_meetings = fields.Integer(dump_only=True)
    total_projects = fields.Integer(dump_only=True)
    total_ca_events = fields.Integer(dump_only=True)

    # group by
    total_users_by_types = fields.List(
        fields.Nested(TotalUserByTypeSchema))
    total_account_by_types = fields.List(
        fields.Nested(TotalAccountByTypeSchema))
    total_webinar_by_types = fields.List(
        fields.Nested(TotalWebinarByTypeSchema))
    total_webcast_by_types = fields.List(
        fields.Nested(TotalWebcastByTypeSchema))
    total_project_by_types = fields.List(
        fields.Nested(TotalProjectByTypeSchema))
    total_meeting_by_types = fields.List(
        fields.Nested(TotalMeetingByTypeSchema))
    total_ca_event_by_types = fields.List(
        fields.Nested(TotalCAEventByTypeSchema))


class AdminDashboardStatsReadArgsSchema(BaseReadArgsSchema):
    pass
