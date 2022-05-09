"""
Schemas for "account managers" related models
"""

from marshmallow import ValidationError, validates_schema

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, account_fields)
from app.resources.account_managers.models import AccountManager
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT


class AccountManagerSchema(ma.ModelSchema):
    """
    Schema for loading "account managers" from request, and also formatting
    output
    """

    class Meta:
        model = AccountManager
        include_fk = True
        load_only = ('updated_by', 'created_by', )
        dump_only = default_exclude + ('updated_by', 'created_by', )

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.accountmanagerapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.accountmanagerlist')
    }, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    manager = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @validates_schema(pass_original=True)
    def validate_account_manager_admin(self, data, original_data):
        """
        validate for account manager type is admin or not
        :param data:
        :param original_data:
        :return:
        """
        error = False
        manager_data = None
        if 'manager_id' in original_data and original_data['manager_id']:
            manager_data = User.query.filter_by(
                row_id=original_data['manager_id']).first()
            if (manager_data and
                    manager_data.account_type != ACCOUNT.ACCT_ADMIN):
                error = True
        if error:
            raise ValidationError('Manager is not admin type', 'manager_id')


class AccountManagerReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "account manager" filters from request args
    """
    pass
