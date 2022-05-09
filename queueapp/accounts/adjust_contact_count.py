"""
account stats related tasks
"""

from sqlalchemy import func
from sqlalchemy.orm import aliased

from app import db
from app.resources.users.models import User
from app.resources.contacts.models import Contact

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def adjust_contact_count(self, result, account_id, blocked, *args, **kwargs):
    """
    Update contact count if account is blocked or unblocked
    stats such as total users
    :param account_id: id of account
    """

    if result:
        try:
            sender = aliased(User)
            sendee = aliased(User)
            sender_query = db.session.query(
                Contact.sent_by.label('user_id'),
                func.count(Contact.sent_by).label('cnt')).join(
                sendee, sendee.row_id == Contact.sent_to).filter(
                sendee.account_id == account_id).group_by(Contact.sent_by)
            sendee_query = db.session.query(
                Contact.sent_to.label('user_id'),
                func.count(Contact.sent_to).label('cnt')).join(
                sender, sender.row_id == Contact.sent_by).filter(
                sender.account_id == account_id).group_by(Contact.sent_to)
            query = sender_query.union_all(sendee_query).subquery()
            query = db.session.query(
                query.c.user_id.label('user_id'),
                func.sum(query.c.cnt).label('cnt')).group_by(
                query.columns.user_id)

            for i in query.all():
                if not blocked:
                    User.query.filter_by(row_id=i.user_id).update({
                        'total_contacts': User.total_contacts + i.cnt
                    }, synchronize_session=False)
                else:
                    User.query.filter_by(row_id=i.user_id).update({
                        'total_contacts': User.total_contacts - i.cnt
                    }, synchronize_session=False)

            db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
