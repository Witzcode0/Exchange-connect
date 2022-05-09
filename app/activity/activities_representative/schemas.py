"""
Schemas for "activity institution" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for
from marshmallow import (
    fields, validate, pre_dump, post_dump, validates_schema, ValidationError, pre_load)

from app import ma
from app.activity.activities_representative.models import ActivityRepresentative
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields


class ActivityRepresentativeSchema(ma.ModelSchema):
    """
    Schema for loading "activity organiser" from request,\
    and also formatting output
    """
    _default_exclude_fields = []
    
    class Meta:
        model = ActivityRepresentative
        include_fk = True
        dump_only = default_exclude

    users = ma.Nested(
        'app.resources.user_profiles.schemas.UserProfileSchema', 
        dump_only=True)
    contacts = ma.Nested(
        'app.crm_resources.crm_contacts.schemas.CRMContactSchema', 
        dump_only=True)

    # activity = ma.Nested(
    #     'app.activities.schemas.ActivitySchema', only=user_fields,
    #     dump_only=True)


class RepresentationSchema(ma.Schema):
    """
    Schema to represent user and crm contact
    """
    # email = fields.String(dump_only=True)
    first_name = fields.String(dump_only=True)
    last_name = fields.String(dump_only=True)
    designation = fields.String(dump_only=True)
    account_id = fields.Integer(dump_only=True)
    row_id = fields.Integer(dump_only=True)
    record_type = fields.String(dump_only=True) 
    user_id = fields.Integer(dump_only=True)
    created_date = fields.Date(dump_only=True)

class RepresentationReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Email log" filters from request args
    """
    # standard db fields
    full_name = fields.String(load_only=True)
    account_id = fields.Integer(load_only=True)
