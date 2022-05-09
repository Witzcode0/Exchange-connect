"""
Schemas for "survey stats" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import BaseReadArgsSchema


class SurveyStatsOverallSchema(ma.Schema):
    """
    Schema to calculate overall stats
    """

    total_published_surveys = fields.Integer(dump_only=True)
    total_responses = fields.Integer(dump_only=True)
    average_response_per_survey = fields.Float(dump_only=True)
    total_surveys = fields.Integer(dump_only=True)
    total_invitees = fields.Integer(dump_only=True)


class SurveyStatsOverAllForInviteeUserSchema(ma.Schema):
    """
    Schema for invitee users
    """
    total_invited_surveys = fields.Integer(dump_only=True)
    total_completed_surveys = fields.Integer(dump_only=True)
    total_live_surveys = fields.Integer(dump_only=True)
    # #TODO: not fully discussed yet
    average_time_spent = fields.Float(default=0, dump_only=True)


class SurveyStatsOverAllReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Survey stats" filters from request args
    """
    pass
