"""
Schemas for "crm distribution list" related models
"""

from marshmallow import (
    fields, validate, pre_dump, validates_schema, ValidationError, pre_load)
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only, joinedload

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.crm_resources.crm_distribution_invitee_lists.models import (
    CRMDistributionInviteeList)

final_user_fields = user_fields + ['crm_contact_grouped']


class CRMDistributionInviteeListSchema(ma.ModelSchema):
    """
    Schema for loading "crm distribution list" from request,
    and also formatting output
    """
    invitee_email = field_for(
        CRMDistributionInviteeList, 'invitee_email', field_class=fields.Email)

    class Meta:
        model = CRMDistributionInviteeList
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by',
                                       'is_mail_sent', 'email_status',
                                       'sent_on')

    user = ma.Nested('app.resources.users.schemas.UserSchema',
                     only=final_user_fields, dump_only=True)


class CRMDistributionInviteeListReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "CRMDistribution List" filters from request args
    """

    invitee_email = fields.String(load_only=True)
    invitee_first_name = fields.String(load_only=True)
    invitee_last_name = fields.String(load_only=True)
