"""
Models for "companies" package.
"""
from sqlalchemy import func, Index

from app import db
from sqlalchemy.dialects.postgresql import JSONB
from app.base.models import BaseModel
from app.base.model_fields import CastingArray, ChoiceString
from app.resources.accounts import constants as ACCOUNT
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry


class Company(BaseModel):

    __tablename__ = 'company'

    identifier = db.Column(db.String(128))
    isin_number = db.Column(db.String(128))
    sedol = db.Column(db.String(128))
    permanent_security_identifier = db.Column(db.String(128))
    company_name = db.Column(db.String(256), nullable=False)
    sector_id = db.Column(db.BigInteger, db.ForeignKey(
        'sector.id', name='company_sector_id_fkey'))
    industry_id = db.Column(db.BigInteger, db.ForeignKey(
        'industry.id', name='company_industry_id_fkey'))
    region = db.Column(db.String(128))
    country = db.Column(db.String(128))
    state = db.Column(db.String(128))
    city = db.Column(db.String(128))
    address = db.Column(db.String(512))
    business_desc = db.Column(db.String(5000))
    website = db.Column(db.String(128))
    telephone_number = db.Column(db.String(128))
    management_profile = db.Column(CastingArray(JSONB))

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='company_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='company_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                             nullable=False)

    __table_args__ = (
        # unique lower case index, i.e case-insensitive unique constraint
        Index('ci_company_unique_name', func.lower(company_name), unique=True),
    )

    creator = db.relationship('User', backref=db.backref(
        'companies', lazy='dynamic'), foreign_keys='Company.created_by')
    sector = db.relationship('Sector', backref=db.backref(
        'companies', lazy='dynamic'))
    industry = db.relationship('Industry', backref=db.backref(
        'companies', lazy='dynamic'))

    def __init__(self, company_name=None, created_by=None, updated_by=None,
                 *args, **kwargs):
        self.company_name = company_name
        self.created_by = created_by
        self.updated_by = updated_by
        super(Company, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Company %r>' % (self.company_name)
