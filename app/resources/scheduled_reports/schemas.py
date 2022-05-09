"""
Schemas for "corporate announcement" related models
"""

from marshmallow import (
    fields, validates_schema, ValidationError, validate)
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, account_fields)
from app.resources.scheduled_reports.models import (
    ScheduledReport, ScheduledReportLog)
from app.resources.scheduled_reports import constants as SCH_REPORT

user_fields = ['row_id', 'email', 'profile.first_name', 'profile.last_name',
               'profile.designation', 'account.row_id',
               'account.account_name', 'account.account_type']


class ScheduledReportSchema(ma.ModelSchema):
    """
    Schema for loading "ScheduledReport" from request, and also
    formatting output
    """
    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['updator', 'logs']

    email = field_for(ScheduledReport, 'email', field_class=fields.Email)
    type = field_for(ScheduledReport, 'type', validate=validate.OneOf(
        SCH_REPORT.SCH_REPORT_TYPES))
    frequency = field_for(ScheduledReport, 'frequency',
                          validate=validate.OneOf(SCH_REPORT.FREQUENCY_TYPES))

    class Meta:
        model = ScheduledReport
        include_fk = True
        load_only = ('deleted', 'account_id', 'created_by', 'updated_by')
        dump_only = default_exclude + (
            'account_id', 'deleted', 'created_by', 'updated_by')

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    updator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    logs = ma.List(ma.Nested(
        'app.resources.scheduled_reports.schemas.ScheduledReportLogSchema',
        only=['sent_at', 'status', 'created_date']))

    @validates_schema()
    def validate_companies(self, data):
        if 'company' in data and not data['company']:
            raise ValidationError('company can not be empty')
        if 'start_from' in data and not data['start_from']:
            raise ValidationError('start_from can not be empty')


class AdminScheduledReportSchema(ScheduledReportSchema):
    logs = ma.List(ma.Nested(
        'app.resources.scheduled_reports.schemas.ScheduledReportLogSchema'))

    class Meta:
        load_only = ('account_id', 'created_by', 'updated_by')


class ApiCallsSchema(ma.Schema):
    name = fields.String(missing=None)
    dataReceived = fields.String(missing=None)
    code = fields.Integer(missing=None)
    reason = fields.String(missing=None)
    error = fields.String(missing=None)


class ScheduledReportLogSchema(ma.ModelSchema):
    """
    Schema for loading "ScheduledReport" from request, and also
    formatting output
    """
    api_calls = ma.List(ma.Nested(ApiCallsSchema))

    class Meta:
        model = ScheduledReportLog
        include_fk = True
        dump_only = default_exclude + ('created_by', 'account_id', 'report_id')


class ScheduledReportReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ScheduledReport" filters from request args
    """
    # standard db fields
    company = fields.String(load_only=True)
    frequency = fields.String(
        load_only=True, validate=validate.OneOf(SCH_REPORT.FREQUENCY_TYPES))


class AdminScheduledReportReadArgsSchema(ScheduledReportReadArgsSchema):
    """
    Admin Schema for reading "ScheduledReport" filters from request args
    """
    # standard db fields
    created_by = fields.Integer(load_only=True)
    account_id = fields.Integer(load_only=True)
    is_active = fields.Boolean(load_only=True)
    deleted = fields.Boolean(load_only=True)


class ScheduledReportsUserwiseSchema(ma.Schema):
    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    count = fields.Integer(dump_only=True)


class ScheduledReportsUserwiseReadArgsSchema(BaseReadArgsSchema):
    account_name = fields.String(load_only=True)
    email = fields.String(load_only=True)
    full_name = fields.String(load_only=True)


class AdminScheduledReportLogReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ScheduledReport" filters from request args
    """
    # standard db fields
    report_id = fields.Integer(load_only=True)
