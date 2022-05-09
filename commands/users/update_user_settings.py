import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only

from app import db
from app.resources.users.models import User
from app.resources.user_settings.models import UserSettings
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry


class UpdateUserSettings(Command):
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
            print('Updating user settings ...')
        try:
            user_all_data = User.query.options(load_only(
                'row_id', 'search_privacy', 'timezone', 'enable_chat')).all()
            sector_data = [f.row_id for f in Sector.query.options(
                load_only('row_id')).all()]
            industry_data = [f.row_id for f in Industry.query.options(
                load_only('row_id')).all()]
            for user in user_all_data:
                if not user.settings:
                    user.settings = UserSettings()
                user.settings.timezone = user.timezone
                user.settings.search_privacy = user.search_privacy
                user.settings.enable_chat = user.enable_chat
                user.settings.search_privacy_sector = sector_data
                user.settings.search_privacy_industry = industry_data
                db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
