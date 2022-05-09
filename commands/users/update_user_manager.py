import datetime

from flask_script import Command, Option

from app import db
from app.resources.users.models import User
from app.resources.account_managers.models import AccountManager
from app.resources.roles.models import Role
from app.resources.roles import constants as ROLE


class UpdateUserManagerRole(Command):
    """
    Command update user's role as a manager which are already manager of any
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
            print('Updating user role id as a manager ...')

        try:
            # get manager role id
            manger_role_id = Role.query.filter_by(
                name=ROLE.ERT_MNG).first().row_id
            # get all user as a manager from account manager
            manager_ids = [m.manager_id for m in AccountManager.query.distinct(
                AccountManager.manager_id).all()]
            # update role id of manager users
            User.query.filter(
                User.row_id.in_(manager_ids)).update(
                {User.role_id: manger_role_id}, synchronize_session=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
