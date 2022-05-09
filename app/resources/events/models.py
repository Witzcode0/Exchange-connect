"""
Models for "events" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString, LCString
from app.resources.events import constants as EVENT
from app.resources.event_invites import constants as EVENT_INVITE
from app.resources.users import constants as USER
from app.resources.event_file_library.models import EventLibraryFile
from app.resources.event_types.models import EventType


# association table for many-to-many event files
eventfiles = db.Table(
    'eventfiles',
    db.Column('event_id', db.BigInteger, db.ForeignKey(
        'event.id', name='eventfiles_event_id_fkey', ondelete="CASCADE"),
        nullable=False),
    db.Column('file_id', db.Integer, db.ForeignKey(
        'event_library_file.id', name='eventfiles_file_id_fkey',
        ondelete="CASCADE"), nullable=False),
    UniqueConstraint('event_id', 'file_id', name='ac_event_id_file_id_key'),
)


class Event(BaseModel):

    __tablename__ = 'event'

    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='event_account_id_fkey', ondelete='CASCADE'),
        nullable=False)
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_updated_by_fkey', ondelete='CASCADE'),
        nullable=False)
    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='event_created_by_fkey', ondelete='CASCADE'),
        nullable=False)
    event_type_id = db.Column(db.BigInteger, db.ForeignKey(
        'event_type.id', name='event_event_type_id_fkey', ondelete='CASCADE'),
        nullable=False)

    place = db.Column(db.String(256))
    company_name = db.Column(db.String(256), nullable=False)
    subject = db.Column(db.String(512), nullable=False)
    description = db.Column(db.String(9216), nullable=False)
    open_to_all = db.Column(db.Boolean, default=False)  # used for rsvp
    public_event = db.Column(db.Boolean, default=False)  # used for public

    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)

    timezone = db.Column(ChoiceString(USER.ALL_TIMEZONES_CHOICES),
                         default=USER.DEF_TIMEZONE)
    language = db.Column(ChoiceString(EVENT.EVENT_LANGUAGE_CHOICES))
    speaker = db.Column(db.String(256))
    host = db.Column(db.String(256))
    contact_person = db.Column(db.String(256))
    contact_number = db.Column(db.String(32))
    contact_email = db.Column(LCString(128))
    dial_in_details = db.Column(db.String(1024))

    deleted = db.Column(db.Boolean, default=False)

    # Event Invite related
    participated = db.Column(db.BigInteger, default=0)
    not_participated = db.Column(db.BigInteger, default=0)
    maybe_participated = db.Column(db.BigInteger, default=0)
    attended_participated = db.Column(db.BigInteger, default=0)
    avg_rating = db.Column(db.Numeric(5, 2), default=0.00)
    # relationship
    creator = db.relationship('User', backref=db.backref(
        'events', lazy='dynamic'), foreign_keys='Event.created_by')
    editor = db.relationship('User', backref=db.backref(
        'updated_events', lazy='dynamic'), foreign_keys='Event.updated_by')
    files = db.relationship(
        'EventLibraryFile', secondary=eventfiles, backref=db.backref(
            'events', lazy='dynamic'), passive_deletes=True)
    event_type = db.relationship('EventType', backref=db.backref(
        'events', lazy='dynamic'), foreign_keys='Event.event_type_id')
    invitees = db.relationship(
        'User', secondary='event_invite', backref=db.backref(
            'events_invited', lazy='dynamic'),
        foreign_keys='[EventInvite.event_id, EventInvite.user_id]',
        passive_deletes=True, viewonly=True)
    participants = db.relationship(
        'User', secondary='event_invite', backref=db.backref(
            'events_participated', lazy='dynamic'),
        foreign_keys='[EventInvite.event_id, EventInvite.user_id]',
        primaryjoin="and_(EventInvite.status == '" + EVENT_INVITE.ACCEPTED +
        "', EventInvite.event_id == Event.row_id)",
        secondaryjoin="EventInvite.user_id == User.row_id", viewonly=True)
    non_participants = db.relationship(
        'User', secondary='event_invite', backref=db.backref(
            'events_not_participated', lazy='dynamic'),
        foreign_keys='[EventInvite.event_id, EventInvite.user_id]',
        primaryjoin="and_(EventInvite.status == '" + EVENT_INVITE.REJECTED +
        "', EventInvite.event_id == Event.row_id)",
        secondaryjoin="EventInvite.user_id == User.row_id", viewonly=True)
    maybe_participants = db.relationship(
        'User', secondary='event_invite', backref=db.backref(
            'events_maybe_participants', lazy='dynamic'),
        foreign_keys='[EventInvite.event_id, EventInvite.user_id]',
        primaryjoin="and_(EventInvite.status == '" + EVENT_INVITE.MAYBE +
        "', EventInvite.event_id == Event.row_id)",
        secondaryjoin="EventInvite.user_id == User.row_id", viewonly=True)
    attended_participants = db.relationship(
        'User', secondary='event_invite', backref=db.backref(
            'events_attend_participants', lazy='dynamic'),
        foreign_keys='[EventInvite.event_id, EventInvite.user_id]',
        primaryjoin="and_(EventInvite.status == '" + EVENT_INVITE.ATTENDED +
        "', EventInvite.event_id == Event.row_id)",
        secondaryjoin="EventInvite.user_id == User.row_id", viewonly=True)

    def __init__(self, subject=None, description=None, *args, **kwargs):
        self.subject = subject
        self.description = description
        super(Event, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<Event %r>' % (self.row_id)
