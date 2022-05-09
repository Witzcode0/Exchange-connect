"""
Models for "reference project parameters" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class RefProjectParameter(BaseModel):

    __tablename__ = 'ref_project_parameter'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_parameter_created_by_fkey'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_parameter_updated_by_fkey'),
        nullable=False)

    project_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_type.id',
        name='ref_project_parameter_project_type_id_fkey'), nullable=False)
    parent_parameter_name = db.Column(db.String(256), nullable=False)
    parameter_name = db.Column(db.String(256), nullable=False)
    has_yes_no = db.Column(db.Boolean, default=False)
    has_value = db.Column(db.Boolean, default=True)
    level = db.Column(db.Integer, default=1)

    # multi column
    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_project_type_id_parent_parameter_name_parameter_name_key',
              project_type_id, func.lower(parent_parameter_name),
              func.lower(parameter_name), unique=True),
    )

    # relationships
    ref_project_type = db.relationship('RefProjectType', backref=db.backref(
        'ref_project_parameters', lazy='dynamic'))

    def __init__(self, created_by=None, updated_by=None,
                 project_type_id=None, parent_parameter_name=None,
                 parameter_name=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.project_type_id = project_type_id
        self.parent_parameter_name = parent_parameter_name
        self.parameter_name = parameter_name
        super(RefProjectParameter, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RefProjectParameter %r>' % (self.row_id)
