"""
Models for "project history" package.
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.toolkit_resources.projects import constants as PROJ


class ProjectHistory(BaseModel):

    __tablename__ = 'project_history'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='project_history_created_by_fkey'), nullable=False)

    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_history_project_id_fkey'), nullable=False)
    project_type_id = db.Column(db.Integer, db.ForeignKey(
        'ref_project_type.id', name='project_history_project_type_id_fkey'))
    project_name = db.Column(db.String(256))

    glossary = db.Column(db.String(256))
    special_instructions = db.Column(db.String(1024))
    link = db.Column(db.String(256))

    deleted = db.Column(db.Boolean)
    is_completed = db.Column(db.Boolean)

    cancelled = db.Column(db.Boolean)
    analyst_requested = db.Column(db.Boolean)

    order_date = db.Column(db.DateTime)  # set at the time of order
    delivery_date = db.Column(db.DateTime)  # set by analyst
    work_area = db.Column(ChoiceString(PROJ.WORK_ARIA_CHOICES))
    dimention = db.Column(
        ChoiceString(PROJ.DIMENTION_TYPES_CHOICES))
    sides_nr = db.Column(db.Integer)
    slides_completed = db.Column(db.Integer)
    status_id = db.Column(db.BigInteger, db.ForeignKey(
        'project_status.id', name='project_history_status_id_fkey'))
    # project parameters
    params = db.Column(JSONB)
    questionnaire = db.Column(JSONB)

    # relationships
    project_type = db.relationship('RefProjectType', backref=db.backref(
        'project_historys', lazy='dynamic'))
    creator = db.relationship('User', backref=db.backref(
        'project_historys', lazy='dynamic'), foreign_keys='ProjectHistory.created_by')
    status = db.relationship(
        'ProjectStatus', backref=db.backref('project_historys', lazy='dynamic'))

    def __init__(self, created_by=None, updated_by=None,
                 project_type_id=None, *args, **kwargs):
        self.created_by = created_by
        self.project_type_id = project_type_id
        super(ProjectHistory, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectHistory %r>' % (self.row_id)
