"""
Models for "webcast answers" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webcasts/__init__


class WebcastAnswer(BaseModel):

    __tablename__ = 'webcast_answer'

    webcast_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast.id', name='webcast_answer_webcast_id_fkey',
        ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.BigInteger, db.ForeignKey(
        'webcast_question.id', name='webcast_answer_question_id_fkey',
        ondelete='CASCADE'), nullable=False)
    answered_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webcast_answer_answered_by_fkey',
        ondelete='CASCADE'), nullable=False)
    answer = db.Column(db.String(512), nullable=False)

    # relationships
    webcast = db.relationship('Webcast', backref=db.backref(
        'webcast_answers', lazy='dynamic', passive_deletes=True))
    answerer = db.relationship('User', backref=db.backref(
        'webcast_answers', lazy='dynamic'))
    question = db.relationship('WebcastQuestion', backref=db.backref(
        'webcast_answers', lazy='dynamic'))

    def __init__(self, question_id=None, *args, **kwargs):
        self.question_id = question_id
        super(WebcastAnswer, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebcastAnswer %r>' % (self.row_id)
