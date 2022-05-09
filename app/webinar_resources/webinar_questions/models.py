"""
Models for "webinar questions" package.
"""

from app import db
from app.base.models import BaseModel
# related model imports done in webinars/__init__


class WebinarQuestion(BaseModel):

    __tablename__ = 'webinar_question'

    webinar_id = db.Column(db.BigInteger, db.ForeignKey(
        'webinar.id', name='webinar_question_webinar_id_fkey',
        ondelete='CASCADE'), nullable=False)
    questioned_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='webinar_question_questioned_by_fkey',
        ondelete='CASCADE'), nullable=False)
    question = db.Column(db.String(512), nullable=False)

    # relationships
    webinar = db.relationship('Webinar', backref=db.backref(
        'webinar_questions', lazy='dynamic', passive_deletes=True))
    questioner = db.relationship('User', backref=db.backref(
        'webinar_questions', lazy='dynamic'))

    def __init__(self, questioned_by=None, *args, **kwargs):
        self.questioned_by = questioned_by
        super(WebinarQuestion, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<WebinarQuestion %r>' % (self.row_id)
