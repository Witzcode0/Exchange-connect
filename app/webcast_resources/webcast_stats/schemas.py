"""
Schemas for "webcast stats" related models
"""

from marshmallow import fields
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, webcast_fields)
from app.webcast_resources.webcast_stats.models import WebcastStats


class WebcastStatsSchema(ma.ModelSchema):
    """
    Schema for loading "webcast stats" from request,
    and also formatting output
    """
    average_rating = field_for(WebcastStats, 'average_rating', as_string=True)

    class Meta:
        model = WebcastStats
        include_fk = True
        dump_only = default_exclude

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webcast_api.webcaststatsapi', row_id='<row_id>'),
        'collection': ma.URLFor('webcast_api.webcaststatslistapi')
    }, dump_only=True)

    webcast = ma.Nested(
        'app.webcast_resources.webcasts.schemas.WebcastSchema',
        only=webcast_fields, dump_only=True)


class WebcastStatsReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webcast stats" filters from request args
    """
    webcast_id = fields.Integer(load_only=True)


class WebcastStatsOverallSchema(ma.Schema):
    """
    Schema to calculate overall stats for total webcasts and participants
    """
    total_webcasts = fields.Integer()
    webcasts_invited = fields.Integer()
    webcasts_attended = fields.Integer()
    webcasts_hosted = fields.Integer()
    webcasts_participated = fields.Integer()


class WebinarStatsOverallReadArgsSchema(BaseReadArgsSchema):
    """
    Schema to calculate overall stats for total webinars and participants
    """
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)
