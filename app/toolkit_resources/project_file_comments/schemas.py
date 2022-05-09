"""
Schemas for "file comments" related models
"""

from marshmallow import fields, validate
from marshmallow_sqlalchemy import field_for

from app import ma
from app.base import constants as APP
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.toolkit_resources.project_file_comments.models import (
    ProjectFileComment)


class ProjectFileCommentSchema(ma.ModelSchema):
    """
    Schema for loading "ProjectFileComment" from request, and also
    formatting output
    """
    _default_exclude_fields = ['project_archive_file', 'seen_comment_users']
    comment = field_for(
        ProjectFileComment, 'comment',
        validate=validate.Length(min=1, error=APP.MSG_NON_EMPTY))

    class Meta:
        model = ProjectFileComment
        include_fk = True
        load_only = ('updated_by', 'created_by')
        dump_only = default_exclude + ('updated_by', 'created_by')

    is_read = fields.Boolean(dump_only=True)
    project_archive_file = ma.Nested(
        'app.toolkit_resources.project_file_archive.schemas.ProjectArchiveFileSchema',
        only=['filename', 'row_id'],
        dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)


class ProjectFileCommentReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ProjectFileComment" filters from request args
    """
    # standard db fields
    project_file_id = fields.Integer(load_only=True)
