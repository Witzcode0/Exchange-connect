"""
Schemas for "corporate access event slots" related models
"""

from marshmallow import fields
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (default_exclude, BaseReadArgsSchema,
                              ca_event_fields)
from app.corporate_access_resources.corporate_access_event_stats.models \
    import CorporateAccessEventStats


class CorporateAccessEventStatsSchema(ma.ModelSchema):
    """
    Schema for loading "corporate access event stats" from request,
    and also formatting output
    """

    average_rating = field_for(CorporateAccessEventStats, 'average_rating',
                               as_string=True, dump_only=True)

    class Meta:
        model = CorporateAccessEventStats
        include_fk = True
        dump_only = default_exclude

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('corporate_access_api.corporateaccesseventstatsapi',
                          row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventstatslistapi')
    }, dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=ca_event_fields, dump_only=True)


class CorporateAccessEventStatsReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate_access_event stats" filters from request args
    """

    corporate_access_event_id = fields.Integer(load_only=True)


class CAESTotalEventByTypeSchema(ma.Schema):
    """
    Schema to represent total events by type for corporate access events
    """
    total = fields.Integer(dump_only=True)
    name = fields.String(dump_only=True)


class CAESTotalAttendeeByTypeSchema(ma.Schema):
    """
    Schema to represent total attendees by account type for
    corporate access events
    """
    total = fields.Integer(dump_only=True)
    account_type = fields.String(dump_only=True)


class CorporateAccessEventStatsOverallSchema(ma.Schema):
    """
    Schema to represent global stats for corporate access events
    """
    total_events = fields.Integer(dump_only=True)
    total_attended = fields.Integer(dump_only=True)
    total_invited = fields.Integer(dump_only=True)
    total_hosted = fields.Integer(dump_only=True)
    total_participated = fields.Integer(dump_only=True)
    total_collaborated = fields.Integer(dump_only=True)
    total_meetings = fields.Integer(dump_only=True)
    total_location = fields.Integer(dump_only=True)
    total_booked = fields.Integer(dump_only=True)
    average_fill_rate = fields.Float(dump_only=True)
    # group by(s)
    total_events_by_event_sub_types = fields.List(
        fields.Nested(CAESTotalEventByTypeSchema), dump_only=True)
    total_attendees_by_account_types = fields.List(
        fields.Nested(CAESTotalAttendeeByTypeSchema), dump_only=True)


class CorporateAccessEventStatsOverallReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate_access_event global stats"
    filters from request args
    """
    started_at_from = fields.DateTime(load_only=True)
    started_at_to = fields.DateTime(load_only=True)
    ended_at_from = fields.DateTime(load_only=True)
    ended_at_to = fields.DateTime(load_only=True)
