"""
Schemas for "email_log" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for
from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError, pre_load,
    post_dump)

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.news_letter.email_logs.models import Emaillogs
from app.news_letter.email_logs import constants as CHOICE

dist_user_fields = ['row_id','email','first_name', ]
dist_user_fields += ['account.' + fld for fld in ['row_id', 'account_name', 'account_type']]

class EmailLogSchema(ma.ModelSchema):
    """
    Schema for loading "Email_log" from request,\
    and also formatting output
    """
    _default_exclude_fields = ['user_id','dist_user_id']
    
    email_sent = field_for(Emaillogs, 'email_sent', validate=validate.OneOf(
        CHOICE.ACTIONS))
    email = fields.String(dump_only=True)
    first_name = fields.String(dump_only=True)
    last_name = fields.String(dump_only=True)
    designation = fields.String(dump_only=True)
    account_name = fields.String(dump_only=True)

    domain = ma.Nested(
        'app.domain_resources.domains.schemas.DomainSchema', only=('row_id','country'),
        dump_only=True)

    class Meta:
        model = Emaillogs
        include_fk = True
        dump_only = default_exclude

    @post_dump(pass_many=True)
    def data_test(self, objs, many):
        for obj in objs:
            for key in obj:
                if obj[key] in [None,'null','nan']:
                    obj[key] = ""


class EmailLogReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Email log" filters from request args
    """
    # standard db fields

    sort_by = fields.List(fields.String(), load_only=True, missing=['created_date'])
    email_sent = fields.String(load_only=True)
    user_id = fields.Integer(load_only=True)
    dist_user_id = fields.Integer(load_only=True)
    created_date = fields.Date(load_only=True)
    started_at_from = fields.Date(load_only=True)
    ended_at_to = fields.Date(load_only=True)
    account_name = fields.String(load_only=True)
    full_name = fields.String(load_only=True)


class EmailLogcountSchema(ma.Schema):
    """
    Schema to represent count of sent, not send and unsubscribe email
    """
    total_sent = fields.Integer(dump_only=True)
    total_notsend = fields.Integer(dump_only=True)
    total_unsubscribe = fields.Integer(dump_only=True)
    total = fields.Integer(dump_only=True)
    created_date = fields.Date(dump_only=True)


class EmailLogCountReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Email log" filters from request args
    """
    # standard db fields
    sort_by = fields.List(fields.String(), load_only=True, missing=['created_date'])
    started_at_from = fields.Date(load_only=True)
    ended_at_to = fields.Date(load_only=True)