"""
Schemas for "crm contact note" related models
"""

from flask import g
from marshmallow import fields, validates_schema, ValidationError, validate
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_, or_

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.crm_resources.crm_contact_notes.models import CRMContactNote
from app.crm_resources.crm_contact_notes import constants as NOTE
from app.crm_resources.crm_contacts.models import CRMContact
from app.resources.contacts.models import Contact
from app.resources.users.models import User


class CRMContactNoteSchema(ma.ModelSchema):
    """
    Schema for loading "CRMContactNote" from request, and also
    formatting output
    """
    note_type = field_for(CRMContactNote, 'note_type', validate=validate.OneOf(
        NOTE.NOTE_TYPES))
    user_ids = fields.List(fields.Integer(), dump_only=True)
    user_id = fields.Integer(dump_only=True)
    _cached_users = None  # while validating existence of user

    class Meta:
        model = CRMContactNote
        include_fk = True
        load_only = ('account_id', 'created_by')
        dump_only = default_exclude + ('account_id', 'created_by',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('crm_api.crmcontactnoteapi', row_id='<row_id>'),
        'collection': ma.URLFor('crm_api.crmcontactnotelistapi')
    }, dump_only=True)

    users = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True))

    @validates_schema(pass_original=True)
    def validate_user_id_exist_as_contact(self, data, original_data):
        """
        Validation for user_id, user_id exists in crm contact or
        connection(Contact) for current_user
        """
        error = False
        self._cached_users = []  # for host_ids valid valid user
        user_ids = []
        not_match_ids = []
        iids_user = []
        if 'user_id' in original_data and original_data['user_id']:
            user_ids.append(original_data['user_id'])
        elif 'user_ids' in original_data and original_data['user_ids']:
            user_ids = original_data['user_ids'][:]
        for iid in user_ids:
            try:
                iids_user.append(int(iid))
            except Exception as e:
                continue
        user_ids = []
        if iids_user:
            users = User.query.filter(User.row_id.in_(iids_user)).all()
            for user in list(users):
                self._cached_users.append(user)
                user_ids.append(user.row_id)
                if 'user_ids' not in original_data:
                    if not CRMContact.query.filter(and_(
                            CRMContact.user_id == user.row_id,
                            CRMContact.created_by == g.current_user['row_id'])
                            ).first():
                        if not Contact.query.filter(or_(
                                and_(Contact.sent_to == user.row_id,
                                     Contact.sent_by == g.current_user['row_id']),
                                and_(Contact.sent_to == g.current_user['row_id'],
                                     Contact.sent_by == user.row_id))
                                ).first():
                            not_match_ids.append(user.row_id)
        not_matched = set(iids_user) - set(user_ids)
        if not_matched:
            raise ValidationError(
                '%s id is not exists' % not_matched,
                'user_ids')
        if not_match_ids:
            raise ValidationError(
                '%s id is not contact or connection' % not_match_ids,
                'user_id')


class CRMContactNoteReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "crm contact notes" filters from request args
    """
    user_id = fields.Integer(load_only=True)
    ca_event_id = fields.Integer(load_only=True)
    webinar_id = fields.Integer(load_only=True)
    webcast_id = fields.Integer(load_only=True)
