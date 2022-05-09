import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only

from app import db
from app.resources.users.models import User
from app.resources.user_settings.models import UserSettings
from app.resources.guest_user.schemas import GuestUserSchema
from app.resources.user_settings.helpers import create_default_user_settings
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry


class AddUserSettings(Command):
    """
    Command to add user settings for missing users

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
            print('Adding user settings ...')
        try:
            user_all_data = User.query.join(UserSettings,
                UserSettings.user_id == User.row_id, isouter=True).filter(
                UserSettings.user_id == None
            ).all()

            remain_users = list(user_all_data)
            for user in remain_users:
                user = create_default_user_settings(user)
                db.session.add(user)
                db.session.commit()

        except Exception as e:
            raise e
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
