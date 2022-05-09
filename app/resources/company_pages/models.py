"""
Models for "company pages" package.
"""

from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.base.model_fields import CastingArray
from app.resources.users.models import User
from app.resources.accounts.models import Account
# ^ above required for relationships


class CompanyPage(BaseModel):

    __tablename__ = 'company_page'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='company_page_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='company_page_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='company_page_account_id_fkey', ondelete='CASCADE'),
        nullable=False, unique=True)

    html_content = db.Column(db.Text())
    css_content = db.Column(db.Text())
    assets = db.Column(CastingArray(JSONB))

    creator = db.relationship('User', backref=db.backref(
        'company_page', lazy='dynamic'), foreign_keys='CompanyPage.created_by')
    account = db.relationship('Account', backref=db.backref(
        'company_page', lazy='dynamic'))

    def __init__(self, html_content=None, css_content=None, created_by=None,
                 updated_by=None, *args, **kwargs):
        self.html_content = html_content
        self.css_content = css_content
        self.created_by = created_by
        self.updated_by = updated_by
        super(CompanyPage, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<CompanyPage %r>' % (self.account_id)
