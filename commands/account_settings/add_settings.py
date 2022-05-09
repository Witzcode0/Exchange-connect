import datetime

from flask_script import Command, Option

from app import db
from app.resources.accounts.models import Account
from app.resources.account_settings.models import AccountSettings


class AddDefaultSettings(Command):
    """
    Command to add default account settings for existing accounts

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False)
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding account settings for existing accounts')

        try:
            accounts = Account.query.order_by(Account.row_id).all()
            batch_size = 100
            curr_count = 0
            for acc in accounts:
                if AccountSettings.query.filter_by(
                        account_id=acc.row_id).first():
                    continue
                curr_count += 1
                acc_sett = AccountSettings(account_id=acc.row_id)
                db.session.add(acc_sett)
                if curr_count >= batch_size:
                    curr_count = 0
                    db.session.commit()
            if curr_count:
                curr_count = 0
                db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
