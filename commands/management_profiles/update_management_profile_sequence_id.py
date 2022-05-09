import datetime

from flask_script import Command, Option

from app import db
from app.resources.account_profiles.models import AccountProfile
from app.resources.management_profiles.models import ManagementProfile


class UpdateManagementProfileSequenceID(Command):
    """
    Update the sequence_id for the management_profiles according to
    the account_profiles
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
            account_profiles = AccountProfile.query.order_by(
                AccountProfile.row_id).all()
            for account_profile in account_profiles:
                management_profiles = ManagementProfile.query.filter_by(
                    account_profile_id=account_profile.row_id).order_by(
                    ManagementProfile.row_id).all()
                count = 1
                for management_profile in management_profiles:
                    management_profile.sequence_id = count
                    count += 1
                    db.session.add(management_profile)
                    db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
