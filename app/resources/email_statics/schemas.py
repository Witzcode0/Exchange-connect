"""
Schemas for "email statics" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.email_statics.models import EmailStatics


class EmailStaticsSchema(ma.ModelSchema):
    """
    Schema for loading "Email Statics" from request, and also
    formatting output
    """

    class Meta:
        model = EmailStatics
        include_fk = True


class EmailStaticsReadArgSchema(BaseReadArgsSchema):
    """
    Schema for reading "Email Statics" filters from request args
    """
    # standard db fields
    sort_by = fields.List(fields.String(), load_only=True, missing=['date'])
    date = fields.Date(load_only=True)
    email = fields.String(load_only=True)
    account_name = fields.String(load_only=True)
    subject = fields.String(load_only=True)
    full_name = fields.String(load_only=True)
    from_date = fields.Date(load_only=True)
    to_date = fields.Date(load_only=True)
    domain_id = fields.Integer(load_only=True)
