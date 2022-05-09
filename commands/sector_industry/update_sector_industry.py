import datetime

from flask_script import Command, Option
from sqlalchemy.orm import load_only
from sqlalchemy import func

from app import db
from app.resources.account_profiles.models import AccountProfile
from app.resources.sectors.models import Sector
from app.resources.industries.models import Industry
from app.resources.user_profiles.models import UserProfile
from app.resources.companies.models import Company


class UpdateSectorIndustryAccountProfile(Command):
    """
    Command to update sector and industry ids using sector and industry name
    in account profile table after validating from sector and industry table.

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
            print('Updating sector and industry...')
        try:
            # sectors
            sector_data_all = Sector.query.options(load_only(
                'row_id', 'name')).all()
            for sector_data in sector_data_all:
                account_profile_data = AccountProfile.query.filter(
                    func.lower(AccountProfile.sector_name) ==
                    sector_data.name.lower()).all()
                for account in account_profile_data:
                    account.sector_id = sector_data.row_id
                    db.session.add(account)
            # industries
            industry_data_all = Industry.query.options(load_only(
                'row_id', 'name')).all()
            for industry_data in industry_data_all:
                account_profile_data = AccountProfile.query.filter(
                    func.lower(AccountProfile.industry_name) ==
                    industry_data.name.lower()).all()
                for account in account_profile_data:
                    account.industry_id = industry_data.row_id
                    db.session.add(account)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')


class UpdateSectorIndustryUserProfile(Command):
    """
    Command to update sector and industry ids using sector and industry name
    in user profile table after validating from sector and industry table.

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
            print('Updating sector and industry...')
        try:
            # sectors
            user_profile_data = UserProfile.query.options(load_only(
                'row_id', 'sector_names', 'sector_ids')).all()
            sector_data_all = Sector.query.options(load_only(
                'row_id', 'name')).all()
            for user in user_profile_data:
                sec_id = []
                for sector_data in sector_data_all:
                    if not user.sector_names:
                        continue
                    for sector in user.sector_names:
                        if sector_data.name.lower() == sector.lower():
                            sec_id.append(sector_data.row_id)
                            user.sector_ids = sec_id
                            db.session.add(user)
            # industries
            user_profile_data = UserProfile.query.options(load_only(
                'row_id', 'industry_names', 'industry_ids')).all()
            industry_data_all = Industry.query.options(load_only(
                'row_id', 'name')).all()
            for user in user_profile_data:
                ind_id = []
                for industry_data in industry_data_all:
                    if not user.industry_names:
                        continue
                    for industry in user.industry_names:
                        if industry_data.name.lower() == industry.lower():
                            ind_id.append(industry_data.row_id)
                            user.industry_ids = ind_id
                            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')


class UpdateSectorIndustryCompany(Command):
    """
    Command to update sector and industry ids using sector and industry name
    in company table after validating from sector and industry table.

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
            print('Updating sector and industry...')
        try:
            # sectors
            sector_data_all = Sector.query.options(load_only(
                'row_id', 'name')).all()
            for sector_data in sector_data_all:
                company_data = Company.query.filter(
                    func.lower(Company.sector_name) ==
                    sector_data.name.lower()).all()
                for company in company_data:
                    company.sector_id = sector_data.row_id
                    db.session.add(company)
            # industries
            industry_data_all = Industry.query.options(load_only(
                'row_id', 'name')).all()
            for industry_data in industry_data_all:
                company_data = Company.query.filter(
                    func.lower(Company.industry_name) ==
                    industry_data.name.lower()).all()
                for company in company_data:
                    company.industry_id = industry_data.row_id
                    db.session.add(company)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
