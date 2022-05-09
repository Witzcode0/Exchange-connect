"""
Schemas for "file archives" related models
"""

from marshmallow import fields, pre_dump, validate
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_
from flask import g

from app import ma, db
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.toolkit_resources.project_file_archive.models import (
    ProjectArchiveFile)
from app.toolkit_resources.project_file_comments.models import (
    ProjectFileComment, commentusers)
from app.toolkit_resources.projects import constants as PROJECT
import app.toolkit_resources.project_file_archive.constants as FILEARCHIVES


class ProjectArchiveFileSchema(ma.ModelSchema):
    """
    Schema for loading "ProjectArchiveFile" from request, and also
    formatting output
    """
    _default_exclude_fields = [
        'project_j', 'project_k', 'project_l', 'comments']
    remarks = field_for(ProjectArchiveFile, 'remarks', validate=[
        validate.Length(max=FILEARCHIVES.REMARKS_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    version = field_for(ProjectArchiveFile, 'version', validate=[
        validate.Length(max=FILEARCHIVES.VERSION_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    category = field_for(ProjectArchiveFile, 'category',
                         validate=validate.OneOf(PROJECT.PROJECT_FILE_CATEGORY))

    # dynamic number for the current user
    unread_comments = fields.Integer(dump_only=True)

    class Meta:
        model = ProjectArchiveFile
        include_fk = True
        load_only = ('deleted', 'account_id', 'updated_by', 'created_by')
        dump_only = default_exclude + ('account_id', 'updated_by', 'deleted',
                                       'created_by')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor(
            'toolkit_api.projectarchivefileapi', row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.projectarchivefilelistapi')
    }, dump_only=True)

    file_url = ma.Url(dump_only=True)

    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    project = ma.Nested(
        'app.toolkit_resources.projects.schemas.ProjectSchema',
        only=['project_name', 'project_type.project_type_name'],
        dump_only=True)
    project_parameter = ma.Nested(
        'app.toolkit_resources.project_parameters.schemas.'
        'ProjectParameterSchema', only=['parent_parameter_name'],
        dump_only=True)
    comments = ma.List(ma.Nested(
        'app.toolkit_resources.project_file_comments.schemas.'
        'ProjectFileCommentSchema', only=['comment', 'creator', 'created_date'],
        dump_only=True))

    @pre_dump
    def loads_urls(self, obj):
        obj.load_urls()
        obj.unread_comments = db.session.query(ProjectFileComment).join(
            commentusers, and_(
                commentusers.c.project_file_comment_id==
                ProjectFileComment.row_id,
                commentusers.c.user_id==g.current_user['row_id']), isouter=True
        ).filter(
            ProjectFileComment.project_file_id==obj.row_id,
            commentusers.c.user_id.is_(None)).count()


class ProjectArchiveFileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "ProjectArchiveFile" filters from request args
    """
    # standard db fields
    file_name = fields.String(load_only=True)
    project_id = fields.Integer(load_only=True, required=True)
    is_draft = fields.Boolean(load_only=True)
    project_type_id = fields.Integer(load_only=True)
    project_name = fields.String(load_only=True)
    account_id = fields.Integer(load_only=True)
    main_filter = fields.String(load_only=True, validate=validate.OneOf(
        FILEARCHIVES.FILE_LISTS))
