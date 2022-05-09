"""
Models for "Email Statics" package.
"""

from sqlalchemy import func, Index
from sqlalchemy import UniqueConstraint
from app.base.model_fields import LCString
from app.base.model_fields import ChoiceString

from app import db
from app.base import constants as APP
from app.base.models import BaseModel
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACCOUNT

class EmailStatics(BaseModel):

    __tablename__ = 'email_static'

    email = db.Column(LCString(128), nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='email_static_user_id_fkey',
        ondelete='CASCADE'))
    dic_user_id = db.Column(db.BigInteger, db.ForeignKey(
        'distribution_list.id', name='email_static_dict_user_id_fkey',
        ondelete='CASCADE'))
    first_name = db.Column(db.String(128))
    last_name = db.Column(db.String(128))
    message_id = db.Column(db.String(128))
    account_name = db.Column(db.String(512))
    account_type = db.Column(ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES))
    date = db.Column(db.Date)
    from_email = db.Column(LCString(128), nullable=False)
    to_email = db.Column(LCString(128), nullable=False)
    subject = db.Column(db.String(128))
    send = db.Column(db.DateTime)
    delivery = db.Column(db.DateTime)
    bounce = db.Column(db.DateTime)
    complaint = db.Column(db.DateTime)
    reject = db.Column(db.DateTime)
    open_time = db.Column(db.DateTime)
    click = db.Column(db.DateTime)
    rendering_failure = db.Column(db.DateTime)
    ip_address = db.Column(db.String(128))
    userAgent = db.Column(db.String(250))
    email_category = db.Column(ChoiceString(APP.EMAIL_TYEPS))

    def __init__(self, email_id=None,
                 *args, **kwargs):
        self.email_id = email_id
        super(EmailStatics, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<EmailStatics %r>' % (self.first_name)
