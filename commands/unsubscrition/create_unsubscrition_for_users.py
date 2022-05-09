import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only

from app import db
from app.resources.users.models import User
from app.resources.unsubscriptions.helpers import create_default_unsubscription


class CreateUnsubscriptionForExitsUsers(Command):
    """
    Command create user's unsubscription default
    account
    :arg verbose: print progress
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
            print('creating unsubscription for users ...')

        try:
            users = User.query.options(load_only('row_id', 'email')).all()
            for user in users:
                create_default_unsubscription(user.email)
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
