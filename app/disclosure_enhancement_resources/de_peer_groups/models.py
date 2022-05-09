"""
Models for "de peer group" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.resources.users.models import User
from app.resources.companies.models import Company
# ^ required for relationship


# association table for many-to-many de_peer_group company
depeermembership = db.Table(
    'depeermembership',
    db.Column('de_peer_group_id', db.BigInteger, db.ForeignKey(
        'de_peer_group.id',
        name='depeermembership_de_peer_group_id_fkey',
        ondelete="CASCADE"), nullable=False),
    db.Column('company_id', db.BigInteger, db.ForeignKey(
        'company.id', name='depeermembership_company_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('company_id', 'de_peer_group_id',
                     name='company_id_de_peer_group_id_key'),
)


class DePeerGroup(BaseModel):

    __tablename__ = 'de_peer_group'

    name = db.Column('name', db.String(256), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='de_peer_group_created_by_fkey',
        ondelete='CASCADE'), nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='de_peer_group_updated_by_fkey',
        ondelete='CASCADE'), nullable=False)

    company_id = db.Column(db.BigInteger, db.ForeignKey(
        'company.id', name='de_peer_group_company_id_fkey',
        ondelete='CASCADE'), nullable=False)

    # relationships
    creator = db.relationship('User', backref=db.backref(
        'de_peer_group', lazy='dynamic'),
        foreign_keys='DePeerGroup.created_by')
    # linked company
    companies = db.relationship(
        'Company', secondary=depeermembership, backref=db.backref(
            'de_peer_group', lazy='dynamic'), passive_deletes=True)
    primary_company = db.relationship('Company', backref=db.backref(
        'primary_de_peer_groups', lazy='dynamic'),
        foreign_keys='DePeerGroup.company_id')

    def __init__(self, *args, **kwargs):
        super(DePeerGroup, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<DePeerGroup %r>' % (self.name)
