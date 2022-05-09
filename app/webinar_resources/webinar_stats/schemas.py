"""
Schemas for "webinar stats" related models
"""

from marshmallow import fields
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, webinar_fields)
from app.webinar_resources.webinar_stats.models import WebinarStats


class WebinarStatsSchema(ma.ModelSchema):
    """
    Schema for loading "webinar stats" from request,
    and also formatting output
    """
    average_rating = field_for(WebinarStats, 'average_rating', as_string=True)

    class Meta:
        model = WebinarStats
        include_fk = True
        dump_only = default_exclude

    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'webinar_api.webinarstatsapi', row_id='<row_id>'),
        'collection': ma.URLFor('webinar_api.webinarstatslistapi')
    }, dump_only=True)

    webinar = ma.Nested(
        'app.webinar_resources.webinars.schemas.WebinarSchema',
        only=webinar_fields, dump_only=True)


class WebinarStatsReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar stats" filters from request args
    """
    webinar_id = fields.Integer(load_only=True)


class WebinarStatsOverallReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "webinar stats overall" filters from request args
    """
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)


class WebinarStatsOverallSchema(ma.Schema):
    """
    Schema to calculate overall stats for total webinars and participants
    """
    total_webinars = fields.Integer()
    webinars_invited = fields.Integer()
    webinars_attended = fields.Integer()
    webinars_hosted = fields.Integer()
    webinars_participated = fields.Integer()
