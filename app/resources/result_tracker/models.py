"""
Models for "Result tracker" package.
"""
from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel


class ResultTrackerGroup(BaseModel):

    __tablename__ = 'result_tracker_group'

    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='result_tracker_user_fkey', ondelete='CASCADE'))
    group_name = db.Column(db.String())
    is_favourite = db.Column(db.Boolean, default=False)

    #manage sequence of the groups
    sequence_id = db.Column(db.Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'group_name',
                         name='result_tracker_user_id_group_name_uniquekey'),
    )

    #relationships
    users = db.relationship('User', backref=db.backref(
        'user_id', lazy='dynamic'))


