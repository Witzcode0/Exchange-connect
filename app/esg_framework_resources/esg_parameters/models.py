"""
Models for "esg parameters" package.
"""

from sqlalchemy import func, Index

from app import db
from app.base.models import BaseModel


class ESGParameter(BaseModel):

    __tablename__ = 'esg_parameter'

    name = db.Column(db.String(256), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='esg_parameter_created_by_fkey'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='esg_parameter_updated_by_fkey'), nullable=False)
    parameter_parent_id = db.Column(db.BigInteger, db.ForeignKey(
        'esg_parameter.id', name='esg_parameter_parameter_parent_id_fkey',
        ondelete='CASCADE'))
    parameter_index = db.Column(db.String(32), nullable=False, unique=True)

    # special form of the parameter index, to be used mainly for sorting
    parameter_sort_index = db.Column(db.String(160),
                                     nullable=False, unique=True)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_esg_parameter_unique_name_parameter_index', func.lower(name),
              parameter_index, unique=True),
    )
    # relationships
    creator = db.relationship('User', backref=db.backref(
        'esg_parameter', lazy='dynamic'), foreign_keys='ESGParameter.created_by')
    children = db.relationship(
        'ESGParameter', backref=db.backref(
            'esg_parameter_parent', remote_side='ESGParameter.row_id',
            uselist=True))

    def __init__(self, name=None, created_by=None, updated_by=None,
                 parameter_index=None, parameter_sort_index=None,
                 parameter_parent_id=None, *args, **kwargs):
        self.name = name
        self.created_by = created_by
        self.updated_by = updated_by
        self.parameter_parent_id = parameter_parent_id
        self.parameter_index = parameter_index
        self.parameter_sort_index = parameter_sort_index
        super(ESGParameter, self).__init__(*args, **kwargs)

    # Method used for sorting the parameter_index
    def generate_sort_index(self):
        parameter_index = self.parameter_index.split('.')
        distributed_parameter_sort_index = ''
        self.parameter_sort_index = ''
        for i in parameter_index:
            if len(i) == 1:
                distributed_parameter_sort_index =\
                    distributed_parameter_sort_index + '0000' + i + '.'
            elif len(i) == 2:
                distributed_parameter_sort_index =\
                    distributed_parameter_sort_index + '000' + i + '.'
            elif len(i) == 3:
                distributed_parameter_sort_index =\
                    distributed_parameter_sort_index + '00' + i + '.'
            elif len(i) == 4:
                distributed_parameter_sort_index =\
                    distributed_parameter_sort_index + '0' + i + '.'
            else:
                distributed_parameter_sort_index =\
                    distributed_parameter_sort_index + i + '.'
        self.parameter_sort_index = distributed_parameter_sort_index[: - 1]
        return self.parameter_sort_index

    def __repr__(self):
        return '<ESGParameter %r>' % (self.row_id)
