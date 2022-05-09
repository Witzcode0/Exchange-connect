"""
Models for "projects" package.
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString
from app.toolkit_resources.projects import constants as PROJ
from app.resources.accounts import constants as ACCT
from app.toolkit_resources.ref_project_sub_type.models import ProjectSubParamGroup
from app.toolkit_resources.project_designers.models import ProjectDesigner
from app.toolkit_resources.project_status.models import ProjectStatus


class Project(BaseModel):

    __tablename__ = 'project'

    # any changes to these fields will be saved to project history
    # field must be present in project_history table too.
    __trackcolumns__ = [
                'project_type_id', 'project_name', 'glossary',
                'special_instructions', 'link', 'deleted', 'is_completed',
                'cancelled', 'analyst_requested', 'order_date',
                'delivery_date', 'work_area', 'dimention', 'sides_nr',
                'slides_completed', 'status_id', 'params', 'questionnaire']

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_updated_by_fkey'), nullable=False)
    # created by admin on behalf of user
    admin_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_admin_id_fkey'))

    # account id of the project
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='project_account_id_fkey'), nullable=False)
    project_type_id = db.Column(db.Integer, db.ForeignKey(
        'ref_project_type.id', name='project_project_type_id_fkey'),
        nullable=False)

    presentation_format_id = db.Column(db.Integer, db.ForeignKey(
        'ref_project_sub_child_type.id', name='project_project_sub_type_presentation_format_id_fkey'),
        nullable=True)
    esg_standard_id = db.Column(db.Integer, db.ForeignKey(
        'ref_project_sub_child_type.id', name='project_project_sub_type_esg_standard_id_fkey'),
                                    nullable=True)
    project_name = db.Column(db.String(256))

    glossary = db.Column(db.String(256))
    special_instructions = db.Column(db.String(1024))
    link = db.Column(db.String(256))  # will be in comma separated

    is_draft = db.Column(db.Boolean, default=True)
    deleted = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)

    percentage = db.Column(db.Numeric(5, 2), default=0)  # progress percentage
    cancelled = db.Column(db.Boolean, default=False)
    # if work area is design , designer may request to assign a analyst
    # just for help, his files wont be shown to client
    analyst_requested = db.Column(db.Boolean, default=False)

    order_date = db.Column(db.DateTime)  # set at the time of order
    delivery_date = db.Column(db.DateTime)  # set by analyst
    work_area = db.Column(ChoiceString(PROJ.WORK_ARIA_CHOICES), nullable=False)
    # for frontend
    dimention = db.Column(
        ChoiceString(PROJ.DIMENTION_TYPES_CHOICES), nullable=False)
    # for specific size parameter
    report_width = db.Column(db.String(32))
    report_height = db.Column(db.String(32))
    # number of slides
    sides_nr = db.Column(db.Integer)
    slides_completed = db.Column(db.Integer, default=0)
    # project parameters
    params = db.Column(JSONB)
    questionnaire = db.Column(JSONB)
    status_id = db.Column(db.BigInteger, db.ForeignKey(
        'project_status.id', name='project_status_id_fkey'), nullable=True)

    # only annual report subtype
    # #TODO: may be change into master table
    annual_report_type = db.Column(db.String(256))

    # theme
    report_theme = db.Column(db.String)
    presentation_format = None
    esg_standard = None

    # ref_proj_sub_parameter = db.Column(db.BigInteger, db.ForeignKey('ProjectSubParamGroup.id', name='project_sub_param_group_id'), nullable=True)

    # relationships
    project_type = db.relationship('RefProjectType', backref=db.backref(
        'projects', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'projects', lazy='dynamic'), foreign_keys='Project.created_by')
    admin = db.relationship('User', backref=db.backref(
        'projects_for_user', lazy='dynamic'), foreign_keys='Project.admin_id')
    account = db.relationship('Account', backref=db.backref(
        'projects', lazy='dynamic'))
    analysts = db.relationship(
        'User', secondary='project_analyst', backref=db.backref(
            'analyst_projects', lazy='dynamic'),
        foreign_keys='[ProjectAnalyst.analyst_id, ProjectAnalyst.project_id]',
        viewonly=True)
    designers = db.relationship(
        'User', secondary='project_designer', backref=db.backref(
            'designer_projects', lazy='dynamic'),
        foreign_keys='[ProjectDesigner.designer_id, ProjectDesigner.project_id]',
        viewonly=True)
    status = db.relationship(
        'ProjectStatus', backref=db.backref('projects', lazy='dynamic'))
    client_files = db.relationship(
        'ProjectArchiveFile',
        backref=db.backref('project_j', lazy='dynamic'),
        foreign_keys='[Project.created_by, Project.row_id]',
        uselist=True,
        primaryjoin="and_(ProjectArchiveFile.created_by==Project.created_by,"
                    "ProjectArchiveFile.deleted==False,"
                    "ProjectArchiveFile.project_id==Project.row_id)",
        viewonly=True)
    analyst_files = db.relationship(
        'ProjectArchiveFile', secondary='project_analyst',
        backref=db.backref('project_k', lazy='dynamic'),
        foreign_keys='[Project.created_by, Project.row_id, '
                     'ProjectArchiveFile.created_by]',
        uselist=True,
        primaryjoin="ProjectAnalyst.project_id == Project.row_id",
        secondaryjoin="and_(ProjectAnalyst.analyst_id == ProjectArchiveFile.created_by,"
                      "ProjectAnalyst.project_id == ProjectArchiveFile.project_id)",
        viewonly=True)
    designer_files = db.relationship(
        'ProjectArchiveFile', secondary='project_designer',
        backref=db.backref('project_l', lazy='dynamic'),
        foreign_keys='[Project.created_by, Project.row_id, '
                     'ProjectArchiveFile.created_by]',
        uselist=True,
        primaryjoin="ProjectDesigner.project_id == Project.row_id",
        secondaryjoin="and_(ProjectDesigner.designer_id == ProjectArchiveFile.created_by,"
                      "ProjectArchiveFile.project_id == ProjectDesigner.project_id)",
        viewonly=True)
    project_sub_parameters = db.relationship('ProjectSubParamGroup', backref=db.backref(
        'ref_proj_sub_parameter', passive_deletes=True),
        uselist=True,
        primaryjoin="ProjectSubParamGroup.project_id == Project.row_id")

    def __init__(self, created_by=None, updated_by=None,
                 account_id=None, project_type_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.account_id = account_id
        self.project_type_id = project_type_id
        super(Project, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Project %r>' % (self.row_id)


class ProjectApx(BaseModel):

    __tablename__ = 'project_apx'

    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    email = db.Column(LCString(128), nullable=False)
    account_name = db.Column(db.String(512), nullable=False)
    account_type = db.Column(ChoiceString(ACCT.PROJECT_APX_ACCT_TYPE_CHOICES),
                             nullable=False)
    # choices
    project_type = db.Column(
        ChoiceString(PROJ.APX_PROJECT_TYPE_CHOICES), nullable=False)
    project_name = db.Column(db.String(256))

    glossary = db.Column(db.String(256))
    special_instructions = db.Column(db.String(1024))
    link = db.Column(db.String(256))  # will be in comma separated

    deleted = db.Column(db.Boolean, default=False)
    is_completed = db.Column(db.Boolean, default=False)
    percentage = db.Column(db.Numeric(5, 2), default=0)  # progress percentage
    cancelled = db.Column(db.Boolean, default=False)
    # if work area is design , designer may request to assign a analyst
    # just for help, his files wont be shown to client
    analyst_requested = db.Column(db.Boolean, default=False)

    order_date = db.Column(db.DateTime)  # set at the time of order
    delivery_date = db.Column(db.DateTime)  # set by analyst
    work_area = db.Column(ChoiceString(PROJ.WORK_ARIA_CHOICES), nullable=False)
    # for frontend
    dimention = db.Column(
        ChoiceString(PROJ.DIMENTION_TYPES_CHOICES), nullable=False)
    # number of slides
    sides_nr = db.Column(db.Integer)
    slides_completed = db.Column(db.Integer, default=0)
    # project parameters
    params = db.Column(JSONB)

    def __init__(self, *args, **kwargs):
        super(ProjectApx, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Project Apx %r>' % (self.row_id)
