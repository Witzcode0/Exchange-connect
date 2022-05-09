"""
Models for "webcast settings" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webcasts/__init__


class WebcastSetting(BaseModel):

    __tablename__ = 'webcast_setting'

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_setting_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_setting_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_setting_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)

    reminder_1 = db.Column(db.DateTime)
    reminder_2 = db.Column(db.DateTime)
    welcome_message = db.Column(db.String(512))
    completion_message = db.Column(db.String(512))
    missed_message = db.Column(db.String(512))

    # Relationship
    creator = db.relationship('User', backref=db.backref(
        'webcast_settings', lazy='dynamic'),
        foreign_keys='WebcastSetting.created_by')
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_settings', lazy='dynamic', passive_deletes=True))

    def __init__(self, created_by=None, updated_by=None,
                 webcast_id=None, *args, **kwargs):
        self.created_by = created_by
        self.updated_by = updated_by
        self.webcast_id = webcast_id
        super(WebcastSetting, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastSetting %r>' % (self.row_id)
