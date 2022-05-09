import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only

from app import db
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.accounts.models import Account


class UpdateUsersAccountIdType(Command):
    """
    Command update user and user profile account id and account type according
    account

    :arg verbose:        print progress
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
            print('Updating account type and id in user and user profile ...')
        try:
            account_data_all = Account.query.options(load_only(
                'row_id', 'account_type')).all()
            for account_data in account_data_all:
                user_data = User.query.filter(
                    User.account_id == account_data.row_id).all()
                for user in user_data:
                    user.account_type = account_data.account_type
                    user.profile.account_id = user.account_id
                    user.profile.account_type = account_data.account_type
                    db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
