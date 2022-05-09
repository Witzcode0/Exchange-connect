"""
Schemas for "contacts" related models
"""

from marshmallow import fields
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base.schemas import default_exclude
from app.resources.email_credentials.models import EmailCredential


class EmailCredentialSchema(ma.ModelSchema):
    """
    Schema for loading "email credential" from request,
    and also formatting output
    """
    from_email = field_for(EmailCredential, 'from_email',
                           field_class=fields.Email)
    smtp_password = fields.String(required=True)

    class Meta:
        model = EmailCredential
        include_fk = True
        dump_only = default_exclude + (
            'created_by', 'account_id', 'is_smtp_active', 'smtp_password')
        load_only = ('smtp_password',)

    user = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=[
            'row_id', 'email'], dump_only=True)

