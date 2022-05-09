"""
Schemas for "activity institution" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for
from marshmallow import (
    fields, validate, pre_dump, post_dump, validates_schema, ValidationError, pre_load)

from app import ma
from app.activity.activities_institution.models import ActivityInstitution, ActivityInstitutionParticipant
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields

# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name', 'account_type', 'domain']


class ActivityInstitutionSchema(ma.ModelSchema):
    """
    Schema for loading "activity institution" from request,\
    and also formatting output
    """
    _default_exclude_fields = []
    
    class Meta:
        model = ActivityInstitution
        include_fk = True
        dump_only = default_exclude

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True) 


class ActivityInstitutionParticipantSchema(ma.ModelSchema):
    """
    Schema for loading "activity institution" from request,\
    and also formatting output
    """
    _default_exclude_fields = []
    
    class Meta:
        model = ActivityInstitutionParticipant
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

class ActivityInstitutionFactSetSchema(ma.Schema):
    """
    Schema to represent factset users
    """
    factset_participant_id = fields.String(dump_only=True)
    full_name = fields.String(dump_only=True)
    designation = fields.String(dump_only=True)
    account_name = fields.String(dump_only=True)
    email = fields.String(dump_only=True)

class ActivityFactSetReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Factset parameter" filters from request args
    """
    # standard db fields
    full_name = fields.String(load_only=True)
    factset_institution_id = fields.String(load_only=True)