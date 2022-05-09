"""
Models for "user settings" package.
"""

from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, CastingArray
from app.resources.accounts import constants as ACCOUNT
from app.resources.users import constants as USER
from app.resources.user_settings import constants as USERSETTINGS
from app.resources.users.models import User
# ^ above required for relationships
from app.resources.designations import constants as DESIG


class UserSettings(BaseModel):

    __tablename__ = 'user_settings'

    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='user_settings_user_id_fkey', ondelete='CASCADE'),
        nullable=False)

    search_privacy = db.Column(db.ARRAY(
        ChoiceString(ACCOUNT.ACCT_TYPES_CHOICES)),
        default=[ACCOUNT.ACCT_CORPORATE,
                 ACCOUNT.ACCT_BUY_SIDE_ANALYST,
                 ACCOUNT.ACCT_SELL_SIDE_ANALYST,
                 ACCOUNT.ACCT_GENERAL_INVESTOR,
                 ACCOUNT.ACCT_PRIVATE, ACCOUNT.ACCT_SME,
                 ACCOUNT.ACCT_CORP_GROUP])
    search_privacy_industry = db.Column(db.ARRAY(db.BigInteger))
    search_privacy_sector = db.Column(db.ARRAY(db.BigInteger))
    search_privacy_designation_level = db.Column(db.ARRAY(
        ChoiceString(DESIG.DES_LEVEL_TYPES_CHOICES)),
        default=[DESIG.DES_LEVEL_BOD, DESIG.DES_LEVEL_MID,
                 DESIG.DES_LEVEL_OTH])
    search_privacy_market_cap_min = db.Column(db.BigInteger, default=0)
    search_privacy_market_cap_max = db.Column(
        db.BigInteger, default=9223372036854775807)

    # for mobile push notification
    android_request_device_ids = db.Column(db.ARRAY(db.String))
    ios_request_device_ids = db.Column(db.ARRAY(db.String))

    timezone = db.Column(ChoiceString(USER.ALL_TIMEZONES_CHOICES),
                         default=USER.DEF_TIMEZONE)
    language = db.Column(ChoiceString(USER.ALL_LANGUAGES_CHOICES),
                         default=USER.DEF_LANGUAGE)

    enable_chat = db.Column(db.Boolean, nullable=False, default=True)
    # allow the admin to access the system on this user's behalf
    allow_admin_access = db.Column(db.Boolean, nullable=False, default=True)

    # email permissions
    # contacts: contact requests
    new_contact_request = db.Column(db.Boolean, default=True)
    contact_request_accepted = db.Column(db.Boolean, default=True)
    # corporate access events: requests, invites
    # invites
    corpaccess_event_invited = db.Column(db.Boolean, default=True)
    corpaccess_event_invite_accepted = db.Column(db.Boolean, default=True)
    corpaccess_slot_inquiry_received = db.Column(db.Boolean, default=True)
    # webinars: invites
    webinar_invited = db.Column(db.Boolean, default=True)
    webinar_invite_accepted = db.Column(db.Boolean, default=True)
    # webcast: invites
    webcast_invited = db.Column(db.Boolean, default=True)
    webcast_invite_accepted = db.Column(db.Boolean, default=True)

    # crm dashboard customize settings
    crm_customize_view = db.Column(
        CastingArray(JSONB), default=USERSETTINGS.CRM_CUSTOMIZE_DEFAULT_VIEWS)

    # #TODO: check if this is required
    deleted = db.Column(db.Boolean, default=False)

    # one-to-one relationship, hence uselist is False
    user = db.relationship('User', backref=db.backref(
        'settings', uselist=False),
        primaryjoin='UserSettings.user_id == User.row_id')

    def __init__(self, user_id=None, *args, **kwargs):
        self.user_id = user_id
        super(UserSettings, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<UserSettings %r>' % (self.row_id)

    def sort_crm_customize_view(self):
        """
        sorting participants according sequence id
        :return:
        """
        if self.crm_customize_view:
            self.crm_customize_view = sorted(
                self.crm_customize_view,
                key=lambda x: x['sequence_id'])
        return
