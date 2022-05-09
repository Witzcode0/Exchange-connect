import datetime
import json

from flask_script import Command, Option
from sqlalchemy import and_

from app import db
from app.resources.accounts.models import Account
from app.resources.follows.models import CFollow
from app.resources.result_tracker.models import ResultTrackerGroup
from app.resources.result_tracker.schemas import ResultTrackerGroupSchema
from app.resources.result_tracker_companies.schemas import ResultTrackerGroupCompaniesSchema
from app.resources.users.models import User


class AddWatchlist(Command):
    """
    Command to add default favourites watchlist
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
            print('Adding watchlist ...')
        try:
            user_list = db.session.query(User).all()
            counter = 1
            for idx, each_user in enumerate(user_list):
                last_sequence_id_group = db.session.query(ResultTrackerGroup). \
                    filter(ResultTrackerGroup.user_id == each_user.row_id). \
                    order_by(ResultTrackerGroup.sequence_id.desc()).first()

                favourite_filter = db.session.query(ResultTrackerGroup). \
                    filter(and_(ResultTrackerGroup.user_id == each_user.row_id,
                                ResultTrackerGroup.group_name == 'Favourites')). \
                    order_by(ResultTrackerGroup.sequence_id.desc()).first()

                if favourite_filter:
                    continue
                last_sequence_id = 0
                if last_sequence_id_group:
                    if last_sequence_id_group.group_name == 'Favourites':
                        continue
                    last_sequence_id = last_sequence_id_group.sequence_id

                data = {
                    'group_name': 'Favourites',
                    'user_id': each_user.row_id,
                    'is_favourite': True,
                    'sequence_id': last_sequence_id + 1
                }
                json_data = json.loads(json.dumps(data))
                result_tracker_group_schema = ResultTrackerGroupSchema()
                data, errors = result_tracker_group_schema.load(json_data)
                if errors:
                    print(errors)
                    exit(1)
                db.session.add(data)
                db.session.commit()

                top_companies = db.session.query(Account). \
                    join(CFollow, Account.row_id == CFollow.company_id). \
                    filter(CFollow.sent_by == each_user.row_id). \
                    order_by(Account.account_name).limit(20).all()
                last_company_sequence_id = 1

                for each_company in top_companies:
                    info = {
                        'group_id': data.row_id,
                        'account_id': each_company.row_id,
                        'sequence_id': last_company_sequence_id,
                        'user_id': each_user.row_id
                    }
                    last_company_sequence_id += 1
                    json_data = json.loads(json.dumps(info))
                    result_tracker_group_companies_schema = ResultTrackerGroupCompaniesSchema()
                    info, errors = result_tracker_group_companies_schema.load(json_data)
                    if errors:
                        print(errors)
                        exit(1)
                    db.session.add(info)
                    db.session.commit()
                print('Counter: ', counter)
        except Exception as e:
            db.session.rollback()
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
