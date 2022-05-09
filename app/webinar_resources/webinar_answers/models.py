"""
Models for "webinar answers" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webinars/__init__


class WebinarAnswer(BaseModel):

    __tablename__ = 'webinar_answer'

    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_answer_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar_question.id', name='webinar_answer_question_id_fkey',
        ondelete='CASCADE'), nullable=False)
    answered_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_answer_answered_by_fkey',
        ondelete='CASCADE'), nullable=False)
    answer = db.Column(db.String(512), nullable=False)

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'webinar_answers', lazy='dynamic', passive_deletes=True))
    answerer = db.relationship('User', backref=db.backref(
        'webinar_answers', lazy='dynamic'))
    question = db.relationship('WebinarQuestion', backref=db.backref(
        'webinar_answers', lazy='dynamic'))

    def __init__(self, question_id=None, *args, **kwargs):
        self.question_id = question_id
        super(WebinarAnswer, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarAnswer %r>' % (self.row_id)
