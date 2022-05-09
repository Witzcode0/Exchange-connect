"""
Models for "e-meeting" package.
"""

from app import db
import datetime
from app.base.models import BaseModel
# related model imports done in toolkit/__init__


class Emeeting(BaseModel):

    __tablename__ = 'e_meeting'

    project_id = db.Column(db.BigInteger, db.ForeignKey(
        'project.id', name='e_meeting_project_id_fkey',
        ondelete='CASCADE'), nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='e_meeting_created_by_fkey'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='e_meeting_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='e_meeting_account_id_fkey'),
        nullable=False)

    meeting_subject = db.Column(db.String(256))
    meeting_agenda = db.Column(db.String(1024))
    meeting_datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    cancelled = db.Column(db.Boolean, default=False)

    url = db.Column(db.String(256))
    presenter_url = db.Column(db.String(256))
    conference_id = db.Column(db.String(128))
    admin_url = db.Column(db.String(256))

    # to check if currently sending emails to invitees in background
    is_in_process = db.Column(db.Boolean, default=False)

    # email on resend mail
    creator_mail_sent = db.Column(db.Boolean, default=False)

    # relationships
    account = db.relationship('Account', backref=db.backref(
        'e_meeting_account', lazy='dynamic'))
    project = db.relationship('Project', backref=db.backref(
        'project_e_meeting', lazy='dynamic', passive_deletes=True))
    creator = db.relationship('User', backref=db.backref(
        'e_meetings_user', lazy='dynamic'), foreign_keys='Emeeting.created_by')
    invitees = db.relationship('User', secondary='e_meeting_invitee',
                               backref=db.backref(
                                   'emeeting_invitees', lazy='dynamic'),
                               foreign_keys='[EmeetingInvitee.invitee_id,'
                               'EmeetingInvitee.e_meeting_id]',
                               passive_deletes=True, viewonly=True)

    def __init__(self, project_id=None, created_by=None, *args, **kwargs):
        self.project_id = project_id
        self.created_by = created_by
        super(Emeeting, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Emeeting %r>' % (self.row_id)
