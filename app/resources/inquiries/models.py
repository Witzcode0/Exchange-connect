"""
Models for "inquiry" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.inquiries import constants as INQUIRY


class Inquiry(BaseModel):

    __tablename__ = 'inquiry'

    inquiry_type = db.Column(ChoiceString(INQUIRY.INQ_TYPE_TYPE_CHOICES),
                             nullable=False, default=INQUIRY.INQT_CONTACT)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(128), nullable=False)
    contact_number = db.Column(db.String(32))
    subject = db.Column(db.String(512))
    message = db.Column(db.String(4096))
    remarks = db.Column(db.String(1024))

    major_sub_type = db.Column(ChoiceString(INQUIRY.INQT_ALL_TYPE_CHOICES))
    # #TODO: future might require a minor sub type
    # minor_sub_type = db.Column(ChoiceString(INQUIRY.INQ_TYPE_TYPE_CHOICES))

    # incase logged-in user
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='inquiry_account_id_fkey', ondelete='SET NULL'))
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='inquiry_domain_id_fkey', ondelete='RESTRICT'),
                          nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='inquiry_created_by_fkey', ondelete='SET NULL'))
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='inquiry_updated_by_fkey', ondelete='SET NULL'))

    # relationships
    editor = db.relationship('User', backref=db.backref(
        'inquiry_edited', lazy='dynamic'), foreign_keys='Inquiry.updated_by')
    creator = db.relationship('User', backref=db.backref(
        'inquiry_created', lazy='dynamic'), foreign_keys='Inquiry.created_by')
    account = db.relationship('Account', backref=db.backref(
        'inquiry_created', lazy='dynamic'), foreign_keys='Inquiry.account_id')

    def __init__(self, name=None, email=None, *args, **kwargs):
        self.name = name
        self.email = email
        super(Inquiry, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Inquiry %r>' % (self.row_id)
