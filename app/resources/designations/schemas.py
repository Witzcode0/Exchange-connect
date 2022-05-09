"""
Schemas for "designation" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.designations.models import Designation
from app.resources.designations import constants as DESIGNATION
from app.resources.accounts import constants as ACCOUNT


class DesignationSchema(ma.ModelSchema):
    """
    Schema for loading "Designation" from request, and also
    formatting output
    """

    name = field_for(Designation, 'name', validate=[
        validate.Length(min=1, error=APP.MSG_NON_EMPTY),
        validate.Length(max=DESIGNATION.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    designation_level = field_for(
        Designation, 'designation_level', validate=validate.OneOf(
            DESIGNATION.DES_LEVEL_TYPES))
    account_type = field_for(
        Designation, 'account_type', validate=validate.OneOf(
            ACCOUNT.ACCT_TYPES))

    class Meta:
        model = Designation
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.designationapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.designationlistapi')
    }, dump_only=True)

    # #TODO: maybe some user property is required later


class DesignationReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "Designation" filters from request args
    """
    # standard db fields
    name = fields.String(load_only=True)
    designation_level = fields.String(
        load_only=True, validate=validate.OneOf(DESIGNATION.DES_LEVEL_TYPES))
    account_type = fields.String(
        load_only=True, validate=validate.OneOf(ACCOUNT.ACCT_TYPES))
