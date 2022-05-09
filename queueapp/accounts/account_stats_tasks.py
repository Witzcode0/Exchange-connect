"""
account stats related tasks
"""

from sqlalchemy import and_, desc

from app import db
from app.resources.accounts.models import Account
from app.resources.account_stats.models import AccountStats
from app.resources.users.models import User

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def update_account_stats(self, result, account_id, *args, **kwargs):
    """
    Update account stats such as total users
    :param account_id: id of account
    """

    if result:
        try:
            user_count = User.query.filter(and_(
                User.account_id == account_id,
                User.deactivated.is_(False),
                User.deleted.is_(False))).count()
            # if user count more then 0
            if user_count and user_count > 0:
                AccountStats.query.filter(
                    AccountStats.account_id == account_id).update(
                    {AccountStats.total_users: user_count},
                    synchronize_session=False)
                db.session.commit()

                if user_count == 1:
                    user = User.query.filter(and_(
                        User.account_id == account_id,
                        User.deactivated.is_(False),
                        User.deleted.is_(False))).order_by(
                        desc(User.row_id)).first()

                    Account.query.filter(and_(
                        Account.row_id == account_id,
                        Account.activation_date.is_(None))).update(
                        {Account.activation_date: user.created_date},
                        synchronize_session=False)
                    db.session.commit()
            # if user count less then zero then account will be deactivate
            # and account stats will be zero
            else:
                Account.query.filter(Account.row_id == account_id).update(
                    {Account.activation_date: None}, synchronize_session=False)

                AccountStats.query.filter(
                    AccountStats.account_id == account_id).update(
                    {AccountStats.total_users: 0},
                    synchronize_session=False)
                db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
