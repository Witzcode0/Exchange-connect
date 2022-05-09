"""
Schemas for "projects" related models
"""
import json

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow_sqlalchemy import field_for
from sqlalchemy.orm import load_only

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.base import constants as APP
from app.resources.users.models import User
from app.toolkit_resources.projects.models import Project, ProjectApx
from app.toolkit_resources.projects import constants as PROJECT
from app.resources.accounts import constants as ACCT
from app.toolkit_resources.ref_project_parameters.models import (
    RefProjectParameter)
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.ref_project_sub_type.models import ProjectSubParamGroup
from app.toolkit_resources.ref_project_sub_type.schemas import ProjectSubParamGroupSchema
from app.toolkit_resources.project_status.schemas import ProjectStatusSchema


# account details that will be passed while populating account relation
account_fields = ['row_id', 'links', 'account_name']
# project type details
proj_type_fields = ['row_id', 'project_type_name', 'estimated_delivery_days']
# project analysts details that will passed while
# populating project analyst relation
proj_analyst_fields = ['row_id', 'project_id', 'analyst_id']
proj_designer_fields = ['row_id', 'project_id', 'designer_id']
# user details that will be passed while populating user relation
analyst_user_fields = user_fields + ['email', 'profile.phone_number']
designer_user_fields = user_fields + ['email', 'profile.phone_number']
project_status_fields = ['row_id', 'sequence', 'name', 'code']
file_archive_fields = ['row_id', 'category', 'filename', 'file_major_type',
                       'remarks', 'file_type', 'file_url', 'version',
                       'is_approved', 'unread_comments']
file_creator_fields = ['creator.row_id', 'creator.email',
                       'creator.profile.first_name',
                       'creator.profile.last_name',
                       'creator.profile.designation']

project_creator_fields = user_fields + ['email', 'profile.phone_number']

class ProjectSchema(ma.ModelSchema):
    """
    Schema for loading "project" from request, and also formatting output
    """

    # default fields to exclude from the schema for speed up
    _default_exclude_fields = ['project_analysts', 'project_chats',
                               'project_parameters', 'project_designers']

    project_name = field_for(Project, 'project_name', validate=[
        validate.Length(max=PROJECT.NAME_MAX_LENGTH,
                        error=APP.MSG_LENGTH_EXCEEDS)])
    glossary = field_for(Project, 'glossary', validate=[validate.Length(
        max=PROJECT.NAME_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])
    special_instructions = field_for(
        Project, 'special_instructions', validate=[validate.Length(
            max=PROJECT.INST_MAX_LENGTH, error=APP.MSG_LENGTH_EXCEEDS)])

    percentage = field_for(Project, 'percentage', as_string=True)
    work_area = field_for(
        Project, 'work_area', validate=validate.OneOf(PROJECT.WORK_ARIAS))
    dimention = field_for(
        Project, 'dimention', validate=validate.OneOf(PROJECT.DIMENTION_TYPES))
    sides_nr = field_for(
        Project, 'sides_nr', validate=validate.Range(min=0))
    slides_completed = field_for(
        Project, 'slides_completed', validate=validate.Range(min=0))

    presentation_format = fields.String(dump_only=True)
    esg_standard = fields.String(dump_only=True)
    project_parameters = ma.List(ma.Nested(
        'app.toolkit_resources.project_parameters.'
        'schemas.ProjectParameterSchema',
        exclude=['project_id', 'account', 'project', 'creator',
                 'project_files']))
    project_files = ma.List(ma.Nested(
        'app.toolkit_resources.project_file_archive.schemas.'
        'ProjectArchiveFileSchema', only=file_archive_fields
    ))
    client_files = ma.List(
        ma.Nested(
            'app.toolkit_resources.project_file_archive.schemas.'
            'ProjectArchiveFileSchema', only=file_archive_fields))
    analyst_files = ma.List(
        ma.Nested(
            'app.toolkit_resources.project_file_archive.schemas.'
            'ProjectArchiveFileSchema',
            only=file_archive_fields+file_creator_fields))
    designer_files = ma.List(
        ma.Nested(
            'app.toolkit_resources.project_file_archive.schemas.'
            'ProjectArchiveFileSchema',
            only=file_archive_fields+file_creator_fields))
    class Meta:
        model = Project
        include_fk = True
        load_only = ('created_by', 'updated_by', 'account_id')
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'account_id', 'is_draft', 'deleted',
            'admin_id', 'is_completed')

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('toolkit_api.projectapi', row_id='<row_id>'),
        'collection': ma.URLFor('toolkit_api.projectlistapi')
    }, dump_only=True)

    account = ma.Nested(
        'app.resources.accounts.schemas.AccountSchema', only=account_fields,
        dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=project_creator_fields,
        dump_only=True)
    admin = ma.Nested(
        'app.resources.users.schemas.UserSchema', only=user_fields,
        dump_only=True)
    project_type = ma.Nested(
        'app.toolkit_resources.ref_project_types.schemas.RefProjectTypeSchema',
        only=proj_type_fields, dump_only=True)
    project_analysts = ma.List(ma.Nested(
        'app.toolkit_resources.project_analysts.schemas.ProjectAnalystSchema',
        only=proj_analyst_fields), dump_only=True)
    project_designers = ma.List(ma.Nested(
        'app.toolkit_resources.project_designers.schemas.ProjectDesignerSchema',
        only=proj_designer_fields), dump_only=True)
    analysts = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=analyst_user_fields),
        dump_only=True)
    designers = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=designer_user_fields),
        dump_only=True)
    status = ma.Nested(
        'app.toolkit_resources.project_status.schemas.ProjectStatusSchema',
        only=project_status_fields)
    project_sub_parameters = ma.List(ma.Nested('app.toolkit_resources.ref_project_sub_type.schemas.ProjectSubParamGroupSchema',
                                       dump_only=True, only=["row_id", "ref_sub_parents", "ref_sub_childs"]))

    @validates_schema(pass_original=True)
    def validate_parent_parameter_name(self, data, original_data):
        """
        Validate Parent parameter name
        """
        error = False
        ref_proj_para_data = None
        pp_names = []
        vpp_names = []
        rids = []

        # get cached project parameters by row_id
        self._cached_project_parameters = {}
        # get the project parameters data from json request
        self._request_project_parameters = {}
        request_proj_params = []
        if 'project_parameters' in original_data:
            request_proj_params = json.loads(original_data['project_parameters'])

        # get parent parameter name from json request data
        if ('project_parameters' in
                original_data and request_proj_params):

            # make query
            ref_proj_para_data = RefProjectParameter.query.filter(
                RefProjectParameter.project_type_id ==
                original_data['project_type_id']).distinct()
            for pp_name in request_proj_params:
                pp_names.append(pp_name['parent_parameter_name'])
            # get valid parent parameter name
            for d in ref_proj_para_data:
                vpp_names.append(d.parent_parameter_name)
            # code for project parameters update
            for rprojpar in request_proj_params:
                try:
                    if rprojpar['row_id'] or rprojpar['row_id'] is None:
                        cur_row_id = rprojpar['row_id']
                        # check new project parameter
                        if cur_row_id is None:
                            cur_row_id = 'None'
                            if (cur_row_id not in
                                    self._request_project_parameters):
                                self._request_project_parameters[
                                    cur_row_id] = []
                            self._request_project_parameters[
                                cur_row_id].append(rprojpar)
                        else:
                            # assign for update project parameter object
                            rids.append(rprojpar['row_id'])
                            self._request_project_parameters[
                                rprojpar['row_id']] = rprojpar
                except Exception as e:
                    continue

            if rids:
                query = ProjectParameter.query.filter(
                    ProjectParameter.row_id.in_(rids)).all()
                for p in query:
                    self._cached_project_parameters[p.row_id] = p

            missing = set(pp_names) - set(vpp_names)
            if missing:
                error = True
        if error:
            raise ValidationError(
                'Parent parameter name: %s does not exist'
                % missing,
                'parent_parameter_names'
            )


class ProjectPutSchema(ProjectSchema):
    """
    Schema for extending project schema for using project_id as dump_only
    in project put functionality
    """
    project_parameters = ma.List(ma.Nested(
        'app.toolkit_resources.project_parameters.'
        'schemas.ProjectParameterSchema',
        exclude=['project_id', 'account', 'project', 'creator']),
        dump_only=True)
    project_parameter_delete_ids = fields.List(fields.Integer, load_only=True)

    class Meta:
        dump_only = default_exclude + (
            'created_by', 'updated_by', 'account_id', 'is_draft', 'deleted',
            'admin_id')


class ProjectReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project" filters from request args
    """
    project_name = fields.String(load_only=True)
    account_name = fields.String(load_only=True)
    project_type_id = fields.Integer(load_only=True)
    is_draft = fields.Boolean(load_only=True)
    is_completed = fields.Boolean(load_only=True)
    cancelled = fields.Boolean(load_only=True)


class ProjectReadAdminArgsSchema(ProjectReadArgsSchema):
    deleted = fields.Boolean(load_only=True)


class ProjectAdminAnalystPutSchema(ProjectPutSchema):
    """
    Schema for loading "project analysts" from request,
    and also formatting output
    """
    analyst_ids = fields.List(fields.Integer(), dump_only=True)
    _cached_analysts = None  # while validating existence of user
    _cached_designers = None
    @validates_schema(pass_original=True)
    def validate_analyst_ids(self, data, original_data):
        """
        Validate that the analyst_ids "users" exist
        """
        error = False
        missing = []
        self._cached_analysts = []
        # load all the analyst ids
        a_ids = []
        if 'analyst_ids' in original_data and original_data['analyst_ids']:
            a_ids = original_data['analyst_ids'][:]
        # validate analyst_ids, and load all the _cached_analysts
        if a_ids:
            # make query
            aids = []
            for f in a_ids:
                try:
                    aids.append(int(f))
                except Exception as e:
                    continue
            self._cached_analysts = [f for f in User.query.filter(
                User.row_id.in_(aids)).options(load_only(
                    'row_id', 'deleted')).all() if not f.deleted]
            analyst_ids = [f.row_id for f in self._cached_analysts]
            missing = set(aids) - set(analyst_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Analysts: %s do not exist' % missing,
                'analyst_ids'
            )

    @validates_schema(pass_original=True)
    def validate_designer_ids(self, data, original_data):
        """
        Validate that the designer_ids "users" exist
        """
        error = False
        missing = []
        self._cached_designers = []
        # load all the analyst ids
        d_ids = []
        if 'designer_ids' in original_data and original_data['designer_ids']:
            d_ids = original_data['designer_ids'][:]
        # validate designer_ids, and load all the _cached_designers
        if d_ids:
            # make query
            dids = []
            for f in d_ids:
                try:
                    dids.append(int(f))
                except Exception as e:
                    continue
            self._cached_designers = [f for f in User.query.filter(
                User.row_id.in_(dids)).options(load_only(
                    'row_id', 'deleted')).all() if not f.deleted]
            designer_ids = [f.row_id for f in self._cached_designers]
            missing = set(dids) - set(designer_ids)
            if missing:
                error = True

        if error:
            raise ValidationError(
                'Designers: %s do not exist' % missing,
                'designer_ids'
            )

class ProjectAdminAnalystPostSchema(ProjectSchema):
    class Meta:
        model = Project
        include_fk = True
        load_only = ('created_by', 'updated_by', 'account_id')
        dump_only = default_exclude + (
            'updated_by', 'is_draft', 'deleted', 'admin_id')

    project_sub_parameters = ma.List(
        ma.Nested('app.toolkit_resources.ref_project_sub_type.schemas.ProjectSubParamGroupSchema',
                  dump_only=True, only=["row_id", "ref_sub_parents", "ref_sub_childs"]))


class ProjectAPXSchema(ma.ModelSchema):

    email = field_for(ProjectApx, 'email', field_class=fields.Email)
    project_type = field_for(
        ProjectApx, 'project_type',
        validate=validate.OneOf(PROJECT.APX_PROJECT_TYPES))
    account_type = field_for(
        ProjectApx, 'account_type',
        validate=validate.OneOf(ACCT.PROJECT_APX_ACCT_TYPES))
    work_area = field_for(
        ProjectApx, 'work_area', validate=validate.OneOf(PROJECT.WORK_ARIAS))
    dimention = field_for(
        ProjectApx, 'dimention', validate=validate.OneOf(PROJECT.DIMENTION_TYPES))
    percentage = field_for(Project, 'percentage', as_string=True)

    class Meta:
        model = ProjectApx
        include_fk = True
        dump_only = default_exclude + (
            'is_draft', 'deleted', 'is_completed')


class ProjectApxReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "project" filters from request args
    """
    project_name = fields.String(load_only=True)
    project_type = fields.String(load_only=True)