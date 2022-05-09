import datetime

from flask_script import Command, Option
from flask_migrate import stamp

from app import db
from app.resources.accounts import constants as ACCOUNT
from app.resources.accounts.models import Account
from app.resources.users.models import User
from app.resources.account_profiles.models import AccountProfile
from app.resources.user_profiles.models import UserProfile
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role, RoleMenuPermission
from app.resources.twitter_feeds.models import TwitterFeedSource
from app.resources.twitter_feeds.models import tweetaccounts
from app.semidocument_resources.research_report_parameters.models import (
    ResearchReportParameter)
from app.toolkit_resources.project_status.models import ProjectStatus
from app.toolkit_resources.project_designers.models import ProjectDesigner
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from app.resources.personalised_video.models import PersonalisedVideoMaster
from app.resources.personalised_video_invitee.models import PersonalisedVideoInvitee
from app.resources.personalised_video_logs.models import PersonalisedVideoLogs

class SetupDB(Command):
    """
    Command to create the db

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
            print('Creating the db...')

        try:
            db.create_all()
            # "stamping" it with the most recent rev:
            stamp(directory='migrations', revision='fb3e7c0e5450')
        except Exception as e:
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')


class SetupDefaultDB(Command):
    """
    Command to setup a default user, account, and roles.

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
        Option('--email', '-eml', dest='email', required=True),
        Option('--password', '-pwd', dest='password', required=True),
        Option('--first_name', '-fn', dest='first_name',
               required=True),
        Option('--last_name', '-ln', dest='last_name', required=True)
    ]

    def run(self, verbose, dry, email, password, first_name, last_name):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding default roles...')

        try:
            # add a default account and profile
            def_account = Account(account_name='Default', created_by=0,
                                  updated_by=0,
                                  account_type=ACCOUNT.ACCT_ADMIN)
            def_account.profile = AccountProfile(
                account_type=ACCOUNT.ACCT_ADMIN)
            db.session.add(def_account)
            def_guest_account = Account(account_name=ACCOUNT.DGA_NAME,
                                        created_by=0, updated_by=0,
                                        account_type=ACCOUNT.ACCT_GUEST)
            def_guest_account.profile = AccountProfile(
                account_type=ACCOUNT.ACCT_GUEST)
            db.session.add(def_guest_account)
            db.session.commit()

            # add a default user and profile
            def_sa = User(email=email, password=password,
                          created_by=0, updated_by=0,
                          account_id=def_account.row_id,
                          f_password_updated=True,
                          account_type=ACCOUNT.ACCT_ADMIN)
            def_sa.profile = UserProfile(first_name=first_name,
                                         last_name=last_name,
                                         account_id=def_account.row_id,
                                         account_type=ACCOUNT.ACCT_ADMIN)
            db.session.add(def_sa)
            db.session.commit()

            # update just created account, with created_by, updated_by fields
            def_account.created_by = def_sa.row_id
            def_account.updated_by = def_sa.row_id
            db.session.add(def_account)
            db.session.commit()

            # add super admin role
            sa_role = Role(
                name=ROLE.ERT_SU, permissions=ROLE.USER_PERMISSIONS,
                created_by=def_sa.row_id, updated_by=def_sa.row_id)
            db.session.add(sa_role)
            db.session.commit()

            # assign super admin role to default user
            def_sa.role_id = sa_role.row_id
            # update user, with created_by, updated_by fields
            def_sa.created_by = def_sa.row_id
            def_sa.updated_by = def_sa.row_id
            db.session.add(def_account)
            db.session.commit()

            # add admin role
            a_role = Role(
                name=ROLE.ERT_AD, permissions=[
                    ROLE.EPT_NU, ROLE.EPT_AR, ROLE.EPT_AM],
                created_by=def_sa.row_id, updated_by=def_sa.row_id)
            db.session.add(a_role)
            db.session.commit()

            # add manager role
            a_role = Role(
                name=ROLE.ERT_MNG, permissions=ROLE.USER_PERMISSIONS,
                created_by=def_sa.row_id, updated_by=def_sa.row_id)
            db.session.add(a_role)
            db.session.commit()

            # add client admin role
            ca_role = Role(
                name=ROLE.ERT_CA, permissions=[ROLE.EPT_NU, ROLE.EPT_AR],
                created_by=def_sa.row_id, updated_by=def_sa.row_id)
            db.session.add(ca_role)
            db.session.commit()

            # add normal role
            n_role = Role(
                name=ROLE.ERT_NO, permissions=[],
                created_by=def_sa.row_id, updated_by=def_sa.row_id)
            db.session.add(n_role)
            db.session.commit()

            # add demo guest role
            g_role = Role(
                name=ROLE.ERT_GUEST, permissions=[],
                created_by=def_sa.row_id, updated_by=def_sa.row_id)
            db.session.add(g_role)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')


class SetupTestDemoDB(Command):
    """
    Command to setup a demo user, account, and assign roles.

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
        Option('--sa', '-sa', dest='sa_id', type=int, required=True),
        Option('--default_account', '-def_accnt', dest='def_ac_id',
               type=int, required=True),
    ]

    def run(self, verbose, dry, sa_id, def_ac_id):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Adding default roles...')

        try:
            # get the super admin user for creating the demo account
            sa_user = User.query.get(sa_id)
            # get the default account
            def_account = Account.query.get(def_ac_id)
            # get admin role
            ad_role = Role.query.filter_by(name=ROLE.ERT_AD).first()
            # get client admin role
            cad_role = Role.query.filter_by(name=ROLE.ERT_CA).first()
            # get normal role
            nor_role = Role.query.filter_by(name=ROLE.ERT_NO).first()

            # add a demo client account
            demo_account = Account(
                account_name='Demo Client', created_by=sa_user.row_id,
                updated_by=sa_user.row_id)
            db.session.add(demo_account)
            db.session.commit()

            # add a demo admin user
            def_admin = User(
                email='demoadmin@example.com', password='demoadmin',
                first_name='Demo', last_name='Admin',
                created_by=sa_user.row_id, updated_by=sa_user.row_id,
                account_id=def_account.row_id, role_id=ad_role.row_id)
            db.session.add(def_admin)
            db.session.commit()

            # add a demo client admin user
            def_cadmin = User(
                email='democlientadmin@example.com',
                password='democlientadmin', first_name='Demo',
                last_name='Client Admin',
                created_by=def_admin.row_id, updated_by=def_admin.row_id,
                account_id=demo_account.row_id, role_id=cad_role.row_id)
            db.session.add(def_cadmin)
            db.session.commit()

            # add a demo normal user
            def_normal = User(
                email='demonormal@example.com', password='demonormal',
                first_name='Demo', last_name='Normal',
                created_by=def_cadmin.row_id, updated_by=def_cadmin.row_id,
                account_id=demo_account.row_id, role_id=nor_role.row_id)
            db.session.add(def_normal)
            db.session.commit()

            # add demo guest role
            g_role = Role(
                name=ROLE.ERT_GUEST, permissions=[],
                created_by=def_cadmin.row_id, updated_by=def_cadmin.row_id)
            db.session.add(g_role)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
