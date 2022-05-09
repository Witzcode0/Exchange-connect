"""
Schemas for "corporate access event agendas" related models
"""

from marshmallow_sqlalchemy import field_for
from marshmallow import ValidationError, validates_schema, validate

from app import ma
from app.base.schemas import (
    default_exclude, ca_event_fields, BaseReadArgsSchema)
from app.base import constants as APP
from app.corporate_access_resources.corporate_access_event_agendas.models \
    import CorporateAccessEventAgenda
from app.corporate_access_resources.corporate_access_events import \
    constants as CAEVENT


class CorporateAccessEventAgendaSchema(ma.ModelSchema):
    """
    Schema for loading "corporate_access_event hosts" from request,
    and also formatting output
    """

    secondary_title = field_for(
        CorporateAccessEventAgenda, 'secondary_title',
        validate=[validate.Length(max=CAEVENT.COMMON_MAX_LENGTH,
                                  error=APP.MSG_LENGTH_EXCEEDS)])

    class Meta:
        model = CorporateAccessEventAgenda
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventagendalistapi')
    }, dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=ca_event_fields, dump_only=True)

    @validates_schema
    def validate_started_at_and_ended_at(self, data):
        """
        Validate started_at and ended_at(ended_at greater then started_at)
        """
        error = False
        if ('started_at' in data and data['started_at'] and
                'ended_at' not in data):
            raise ValidationError(
                'Please provide end date', 'ended_at')
        elif ('ended_at' in data and data['ended_at'] and
                'started_at' not in data):
            raise ValidationError(
                'Please provide start date', 'started_at')
        elif ('started_at' in data and data['started_at'] and
                'ended_at' in data and data['ended_at']):
            if data['started_at'] > data['ended_at']:
                error = True

        if error:
            raise ValidationError(
                'End date should be greater than Start date',
                'started_at, ended_at')


class CorporateAccessEventAgendaReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate_access_event agenda" filters from request
    args
    """
    pass
