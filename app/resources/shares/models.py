"""
Models for "shares" package.
"""

from sqlalchemy import UniqueConstraint

from app import db
from app.base.models import BaseModel
from app.base.model_fields import ChoiceString
from app.resources.users.models import User


# # association table for many-to-many user table
# shareusers = db.Table(
#     'shareusers',
#     db.Column('share_id', db.Integer, db.ForeignKey(
#         'share.id', ondelete="CASCADE"), nullable=False),
#     db.Column('user_id', db.Integer, db.ForeignKey(
#         'user.id', ondelete="CASCADE"), nullable=False),
#     UniqueConstraint('share_id', 'user_id', name='ac_share_id_user_id_key'),
# )

# #TODO: may be implement in future
class Share(BaseModel):

    # __tablename__ = 'share'
    # # user who posted a post
    # shared_by = db.Column(db.Integer, db.ForeignKey('user.id'),
    #                       nullable=False)
    # post_id = db.Column(db.BigInteger, db.ForeignKey('post.id'),
    #                     nullable=False)
    # share_type = db.Column(ChoiceString(SHARE.SHARE_TYPES_CHOICES),
    #                        default=SHARE.SHARE_PUB)
    #
    # description = db.Colunm(db.String(2048))
    #
    # # relationships
    # # linked users
    # shared_to = db.relationship(
    #     'User', secondary=shareusers, backref=db.backref(
    #         'shares', lazy='dynamic'), passive_deletes=True)
    #
    # def __init__(self, *args, **kwargs):
    #     super(Share, self).__init__(*args, **kwargs)
    #
    # def __repr__(self):
    #     return '<share %r>' % (self.description)
    pass
