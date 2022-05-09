"""
Models for "project types" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class RefProjectSubChildType(BaseModel):

    __tablename__ = 'ref_project_sub_child_type'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_sub_type_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ref_project_sub_type_updated_by_fkey'), nullable=False)

    project_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_type.id',
        name='ref_project_sub_type_id_fkey'), nullable=False)

    ref_child_parameters = db.Column(db.BigInteger, db.ForeignKey(
        'ref_project_sub_type.id',
        name='ref_project_sub_type_ref_parent_id_fkey'), nullable=False)

    child_title = db.Column(db.String(256), nullable=False)
    child_id = db.Column(db.Integer, nullable=False)

    #relationships
    ref_sub_parents = db.relationship('RefProjectSubType', backref=db.backref(
        'ref_child_parameters', passive_deletes=True),
                             primaryjoin='RefProjectSubChildType.ref_child_parameters == RefProjectSubType.row_id')

    def __init__(self, created_by=None, updated_by=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        super(RefProjectSubChildType, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RefProjectSubChildType %r>' % (self.row_id)