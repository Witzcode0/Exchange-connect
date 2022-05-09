import datetime

from flask_script import Command, Option

from app import db
from app.resources.accounts.models import Account
from app.resources.users.models import User


class UpdateUserSequenceID(Command):
    """
    Update the sequence_id for the users according to accounts
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
            print('Updating sequence_id ...')
        try:
            accounts = Account.query.order_by(
                Account.row_id).all()
            for account in accounts:
                users = User.query.filter_by(
                    account_id=account.row_id).order_by(
                    User.row_id).all()
                count = 1
                for user in users:
                    user.sequence_id = count
                    count += 1
                    db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
