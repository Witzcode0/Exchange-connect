"""
Models for "registration requests" package.
"""

from app import db
from app.base.models import BaseModel
from app.base.model_fields import LCString, ChoiceString
from werkzeug.security import generate_password_hash
from app.resources.accounts import constants as ACCOUNT
from app.resources.registration_requests import constants as REGREQUEST


class RegistrationRequest(BaseModel):

    __tablename__ = 'registration_request'

    email = db.Column(LCString(128), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(128), nullable=False)
    last_name = db.Column(db.String(128), nullable=False)
    company = db.Column(db.String(256))
    designation = db.Column(db.String(128))
    phone_number = db.Column(db.String(32))
    join_as = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES),
                        nullable=False, default=ACCOUNT.ACCT_GENERAL_INVESTOR)
    other_selected = db.Column(db.Boolean, default=False)

    status = db.Column(ChoiceString(REGREQUEST.REQ_STATUS_TYPES_CHOICES),
                       nullable=False, default=REGREQUEST.REQ_ST_UNVERIFIED)
    updated_by = db.Column(db.BigInteger)
    deleted = db.Column(db.Boolean, default=False)
    accepted_terms = db.Column(db.Boolean, default=False)
    domain_id = db.Column(db.BigInteger, db.ForeignKey(
        'domain.id', name='registration_request_domain_id_fkey',
        ondelete='RESTRICT'), nullable=True)
    # when registration requested by admin for user
    by_admin = db.Column(db.Boolean, default=False)
    # from design lab identification
    only_design_lab = db.Column(db.Boolean, default=False)

    welcome_mail_sent = db.Column(db.Boolean, default=False)

    domain = db.relationship('Domain', backref=db.backref(
        'registration_requests', uselist=True),
        primaryjoin='RegistrationRequest.domain_id == Domain.row_id')

    def __init__(self, email=None, password=None, first_name=None,
                 last_name=None, *args, **kwargs):
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        if not self.row_id:
            self.set_password(password)
        super(RegistrationRequest, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<RegistrationRequest %r>' % (self.email)

    def set_password(self, password):
        self.password = generate_password_hash(password)
