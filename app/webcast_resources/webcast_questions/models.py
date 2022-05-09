"""
Models for "webcast questions" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webcasts/__init__


class WebcastQuestion(BaseModel):

    __tablename__ = 'webcast_question'

    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_question_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)
    questioned_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_question_questioned_by_fkey',
        ondelete='CASCADE'), nullable=False)
    question = db.Column(db.String(512), nullable=False)

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_questions', lazy='dynamic', passive_deletes=True))
    questioner = db.relationship('User', backref=db.backref(
        'webcast_questions', lazy='dynamic'))

    def __init__(self, questioned_by=None, *args, **kwargs):
        self.questioned_by = questioned_by
        super(WebcastQuestion, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastQuestion %r>' % (self.row_id)
