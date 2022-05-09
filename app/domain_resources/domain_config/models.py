"""
Models for "domain config" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, UCString
from app.domain_resources.domains.models import Domain


class DomainConfig(BaseModel):

    __tablename__ = 'domain_config'

    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='domain_config_domain_id_fkey',
        ondelete='CASCADE'), nullable=False)
    name = db.Column(UCString(512), nullable=False)
    value = db.Column(db.String(), nullable=False)

    # relationships
    domain = db.relationship('Domain', backref=db.backref(
        'domain_configs', uselist=True, passive_deletes=True))

    def __init__(self, domain_id=None, name=None, value=None, *args, **kwargs):
        self.domain_id = domain_id
        self.name = name
        self.value = value
        super(DomainConfig, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Domain Config {}>'.format(self.row_id)
