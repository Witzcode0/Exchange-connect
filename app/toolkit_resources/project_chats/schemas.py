"""
Schemas for "project_chats" related models
"""

from marshmallow import fields

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.toolkit_resources.project_chats.models import ProjectChatMessage


class ProjectChatMessageSchema(ma.ModelSchema):
    """
    Schema for loading "project_chat_message" from request,\
    and also formatting output
    """
    class Meta:
        model = ProjectChatMessage
        include_fk = True
        dump_only = default_exclude + ('sent_by',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('toolkit_api.projectchatmessageapi',
                          row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.projectchatmessagelistapi')
    }, dump_only=True)

    project = ma.Nested(
        'app.toolkit_resources.projects.schemas.ProjectSchema',
        only=['row_id'], dump_only=True)

    sender = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class ProjectChatMessageReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project_chat_message" filters from request args
    """
    project_id = fields.Integer(load_only=True)
    sent_by = fields.Integer(load_only=True)
