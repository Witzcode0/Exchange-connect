'''
Association model to combine news and announcement of particular account
'''

from app import db
from app.base.models import BaseModel
from app.resources.accounts.models import Account
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.news.models import NewsItem


class NewsAnnouncements(BaseModel):

    __tablename__ = 'news_announcements'

    announcements_id = db.Column(db.BigInteger, db.ForeignKey(
        'corporate_announcement.id', name='announcement_id_fkey',
        ondelete='CASCADE'))
    account_id = db.Column(db.BigInteger, db.ForeignKey(
        'account.id', name='account_announcement_id_fkey',
        ondelete='CASCADE'))
    news_id = db.Column(db.BigInteger, db.ForeignKey(
        'news_item.id', name='news_id_fkey', ondelete='CASCADE'))
    market_permission_id = db.Column(db.BigInteger, db.ForeignKey(
        'market_performance.id', name='market_performance_id_fkey',
        ondelete='CASCADE'))
    market_comment_id = db.Column(db.BigInteger, db.ForeignKey(
        'market_analyst_comment.id', name='market_comment_id_fkey',
        ondelete='CASCADE'))
    market_permission_choice = db.Column(db.Boolean, default=False)

    def __init__(self, *args, **kwargs):
        super(NewsAnnouncements, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<NewsAnnouncements row_id=%r>' % (
            self.row_id)
