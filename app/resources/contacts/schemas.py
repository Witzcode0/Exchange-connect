"""
Schemas for "contact" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from flask import g, current_app
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.contacts.models import Contact, ContactHistory
from app.resources.users.models import User
from app.resources.accounts import constants as ACCOUNT


# user details that will be passed while populating user relation
contact_user_fields = user_fields + ['email', 'profile.address_city',
                                     'profile.address_country']


class ContactSchema(ma.ModelSchema):
    """
    Schema for formatting contacts
    """

    class Meta:
        model = Contact
        include_fk = True
        dump_only = default_exclude
        exclude = ('connected_j', )

    links = ma.Hyperlinks({
        'self': ma.URLFor('api.contactapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.contactlistapi')
    }, dump_only=True)

    sender = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=contact_user_fields,
        dump_only=True)
    sendee = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=contact_user_fields,
        dump_only=True)
    the_other = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=contact_user_fields,
        dump_only=True)


class ContactHistorySchema(ma.ModelSchema):
    """
    Schema for contact history
    """
    class Meta:
        model = ContactHistory


class ContactReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for read args
    """
    full_name = fields.String(load_only=True)
    account_type = fields.String(load_only=True, validate=validate.OneOf(
        ACCOUNT.ACCT_TYPES))
    sector_id = fields.Integer(load_only=True)
    industry_id = fields.Integer(load_only=True)


class AdminContactReadArgsSchema(ContactReadArgsSchema):
    """
    Schema for read args by admin
    """
    user_id = fields.Integer(load_only=True)


class ContactAddByQRCodeSchema(ma.ModelSchema):
    """
    Schema for contact add by QR code
    """

    class Meta:
        model = Contact
        include_fk = True
        dump_only = default_exclude + ('sent_by', )

    # #TODO: may be used in future
    # @validates_schema(pass_original=True)
    def valid_account_type_of_sent_to_user(self, data, original_data):
        """
        validation for sent_to user of account type such as if sent_to user
        is corporate so sent_to user can't send request other corporate user,
        he/her only sent request other account type users
        """
        user_data = None
        user_data = User.query.filter(
            User.row_id == original_data['sent_to']).options(load_only(
                'account_type', 'account_id', 'row_id')).first()

        if user_data:
            if (g.current_user['account_type'] == user_data.account_type and
                    g.current_user['account_id'] != user_data.account_id):
                raise ValidationError(
                    'Can not send request to same company type', 'sent_to')
