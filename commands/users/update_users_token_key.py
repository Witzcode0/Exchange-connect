import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only

from app import db
from app.resources.users.models import User
from app.resources.users.helpers import generate_user_random_string


class UpdateUsersTokenKey(Command):
    """
    Command to update user settings according to user

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
            print('Updating users token key ...')
        try:
            user_all_data = User.query.options(load_only(
                'row_id', 'token_key')).all()

            for user in user_all_data:
                user.token_key = generate_user_random_string()
                db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

    print('---' + str(datetime.datetime.utcnow()) + '---')
    print('Done')
