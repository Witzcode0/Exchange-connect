import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import and_

from app import db
from app.resources.accounts.models import Account
from app.resources.account_stats.models import AccountStats
from app.resources.users.models import User


class UpdateAccountStats(Command):
    """
    Command to update stats of account

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('updating account stats')

        try:
            account_ids = [a.row_id for a in Account.query.options(
                load_only('row_id')).all()]
            if account_ids:
                for account_id in account_ids:
                    user_count = User.query.filter(and_(
                        User.account_id == account_id,
                        User.deleted.is_(False))).count()
                    db.session.add(AccountStats(
                        account_id=account_id, total_users=user_count))
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
