"""
Models for "project types" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
from app.toolkit_resources.ref_project_sub_child_type.models import RefProjectSubChildType

class ProjectSubParamGroup(BaseModel):
    __tablename__ = 'projectsubparameters'

    project_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_type.id', name='ref_project_type_id_fkey',
        ondelete='CASCADE'))
    sub_parameter_id = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_sub_type.id', name='ref_project_sub_type_id_fkey',
        ondelete='CASCADE'))
    child_parameter_id = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_sub_child_type.id', name='ref_project_sub_child_type_id_fkey',
        ondelete='CASCADE'))
    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='project_sub_param_group_project_id_fkey',
        ondelete='CASCADE'), nullable=False)

    #relationships
    ref_sub_parents = db.relationship('RefProjectSubType', backref=db.backref(
        'sub_parameter_id', passive_deletes=True),
                                      primaryjoin='ProjectSubParamGroup.sub_parameter_id == RefProjectSubType.row_id')
    ref_sub_childs = db.relationship('RefProjectSubChildType', backref=db.backref(
        'child_parameter_id', passive_deletes=True),
                                      primaryjoin='ProjectSubParamGroup.child_parameter_id == RefProjectSubChildType.row_id')


    def __init__(self, project_type_id=None, *args, **kwargs):
        self.project_type_id = project_type_id
        super(ProjectSubParamGroup, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<ProjectSubParamGroup %r>' % (self.project_type_id)


class RefProjectSubType(BaseModel):

    __tablename__ = 'ref_project_sub_type'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_sub_type_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_sub_type_updated_by_fkey'), nullable=False)

    project_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_type.id',
        name='ref_project_sub_type_id_fkey'), nullable=False)

    parent_title = db.Column(db.String(256), nullable=False)
    parent_id = db.Column(db.Integer, nullable=False)

    #relationships
    # ref_project_type = db.relationship('RefProjectType', backref=db.backref(
    #     'ref_project_sub_type', lazy='dynamic'))


    # multi column
    # __table_args__ = (
    #     # unique lower case index, i.e case-insensitive unique constraint
    #     Index('ci_ref_project_type_unique_project_type_name', func.lower(
    #         project_type_name), unique=True),
    # )

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(RefProjectSubType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RefProjectSubType %r>' % (self.row_id)


