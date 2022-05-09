"""
Schemas for "corporate access event collaborators" related models
"""

from marshmallow import fields, validate, pre_load

from app import ma
from app.base.schemas import (
    default_exclude, BaseReadArgsSchema, user_fields, ca_event_fields)
from app.corporate_access_resources.corporate_access_event_collaborators.\
    models import CorporateAccessEventCollaborator
from app.corporate_access_resources.corporate_access_event_collaborators \
    import constants as COLLB


class CorporateAccessEventCollaboratorSchema(ma.ModelSchema):
    """
    Schema for loading "corporate_access_event collaborators" from request,
    and also formatting output
    """
    permissions = fields.List(fields.String(validate=validate.OneOf(
        COLLB.COL_PER_TYPES)))

    class Meta:
        model = CorporateAccessEventCollaborator
        include_fk = True
        load_only = ('created_by', 'updated_by')
        dump_only = default_exclude + ('created_by', 'updated_by',
            'is_mail_sent','email_status')
        exclude = ('collaborator_j',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'corporate_access_api.corporateaccesseventcollaboratorapi',
            row_id='<row_id>'),
        'collection': ma.URLFor(
            'corporate_access_api.corporateaccesseventcollaboratorlistapi')
    }, dump_only=True)

    collaborator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    corporate_access_event = ma.Nested(
        'app.corporate_access_resources.'
        'corporate_access_events.schemas.CorporateAccessEventSchema',
        only=ca_event_fields, dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)

    @pre_load(pass_many=True)
    def permission_none(self, objs, many):
        """
        When permission is none so remove from object
        """
        if 'permissions' in objs and not objs['permissions']:
            objs.pop('permission')


class CorporateAccessEventCollaboratorReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "corporate_access_event collaborators"
    filters from request args
    """
    collaborator_id = fields.Integer(load_only=True)
    corporate_access_event_id = fields.Integer(load_only=True)
