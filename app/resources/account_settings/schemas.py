"""
Schemas for "account settings" related models
"""

from marshmallow import fields
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude, account_fields
from app.resources.account_settings.models import AccountSettings


class AccountSettingsSchema(ma.ModelSchema):
    """
    Schema for loading "account settings" from request, and also formatting
    output
    """
    event_sender_email = field_for(
        AccountSettings, 'event_sender_email', field_class=fields.Email)

    class Meta:
        model = AccountSettings
        include_fk = True
        load_only = ('deleted',)
        dump_only = default_exclude + (
            'event_sender_verified', 'event_sender_domain_verified', 'deleted')
        exclude = ('ses_email_verification_response',
                   'ses_email_verification_status_response')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.accountsettingsapi')
    }, dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
