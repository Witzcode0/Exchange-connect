"""
Schemas for "guest user" related models
"""

from app import ma
from app.base.schemas import default_exclude
from app.resources.users.schemas import UserSchema
from app.resources.users.models import User


class GuestUserSchema(UserSchema):
    """
    Schema for loading "guest user" from request, and also formatting output
    """

    class Meta:
        model = User
        load_only = (
            'deleted', 'updated_by', 'created_by', 'password', 'unverified',
            'role_id', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'created_by', 'deleted', 'unverified', 'is_admin',
            'account_id', 'role_id', 'account_type', 'sequence_id')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.guestuserapi', row_id='<row_id>'),
    }, dump_only=True)
