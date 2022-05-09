import datetime
import time

from flask_script import Command, Option
from sqlalchemy import and_

from app.resources.accounts.models import Account
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.corporate_access_resources.corporate_access_events.models import (
    CorporateAccessEvent)
from app.resources.user_profiles.models import UserProfile
from app.crm_resources.crm_contacts.models import CRMContact
from app.webinar_resources.webinars.models import Webinar
from app.webcast_resources.webcasts.models import Webcast
from app.crm_resources.crm_distribution_lists.models import CRMDistributionList
from app.base import constants as APP
from app.global_search.helpers import es

from app.global_search.helpers import add_to_index, remove_index


class ElasticReindex(Command):
    """
    Command to re index create documents in elastic search

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
            print('Creating the template...')

        try:
            started_time = time.clock()
            print('started')
            index = APP.DF_ES_INDEX
            remove_index(index)
            settings = {
                "settings": {
                    "number_of_shards": 4,
                    "number_of_replicas": 1
                },
                "mappings": {
                    index: {
                        "properties": {
                            "account_name": {
                                "type": "text",
                                "index": True
                            },
                            "category": {
                                "type": "keyword",
                                "index": True
                            },
                            "subject": {
                                "type": "text",
                                "index": True
                            },
                            "description": {
                                "type": "text",
                                "index": True
                            },
                            "title": {
                                "type": "text",
                                "index": True
                            },
                            "user_emails": {
                                "type": "keyword",
                                "index": True
                            },
                            "module": {
                                "type": "keyword",
                                "index": True
                            },
                            "open_to_all": {
                                "type": "boolean"
                            },
                            "is_draft": {
                                "type": "boolean"
                            },
                            "cancelled": {
                                "type": "boolean"
                            },
                            "created_by": {
                                "type": "long"
                            },
                            "first_name": {
                                "type": "text",
                                "index": True
                            },
                            "middle_name": {
                                "type": "text",
                                "index": True
                            },
                            "last_name": {
                                "type": "text",
                                "index": True
                            },
                            "full_name": {
                                "type": "text",
                                "index": True
                            },
                            "full_name_r": {
                                "type": "text",
                                "index": True
                            },
                            "company": {
                                "type": "text",
                                "index": True
                            },
                            "designation": {
                                "type": "text",
                                "index": True
                            },
                            "open_to_account_types": {
                                "type": "keyword",
                                "index": True
                            },
                            "open_to_public": {
                                "type": "boolean"
                            },
                            "priority": {
                                "type": "integer"
                            },
                            "search_privacy": {
                                "type": "keyword",
                                "index": True
                            },
                            "search_privacy_designation_level": {
                                "type": "keyword",
                                "index": True
                            },
                            "search_privacy_industry": {
                                "type": "integer"
                            },
                            "search_privacy_sector": {
                                "type": "integer"
                            },
                            "search_privacy_market_cap_min": {
                                "type": "long"
                            },
                            "search_privacy_market_cap_max": {
                                "type": "long"
                            },
                            "account_type_preference": {
                                "type": "keyword",
                                "index": True
                            },
                            "account": {
                                "type": "object",
                                "properties": {
                                    "account_name": {
                                        "type": "text",
                                        "index": True
                                    },
                                    "account_type": {
                                        "type": "keyword",
                                        "index": True
                                    },
                                    "sector_name": {
                                        "type": "keyword",
                                        "index": True
                                    },
                                    "industry_name": {
                                        "type": "keyword",
                                        "index": True
                                    },
                                    "country": {
                                        "type": "keyword",
                                        "index": True
                                    },
                                    "blocked": {
                                        "type": "boolean"
                                    },
                                    "domain_id": {
                                        "type": "long"
                                    },
                                },
                            },
                        }
                    }
                }
            }
            es.indices.create(index=index, body=settings)
            elastic_tables = [
                              Account,
                              CorporateAnnouncement,
                              CorporateAccessEvent,
                              UserProfile,
                              CRMContact,
                              Webinar,
                              Webcast,
                              CRMDistributionList,
                              ]
            for table in elastic_tables:
                query = table.query
                if hasattr(table, 'deleted'):
                    query = query.filter(table.deleted==False)

                for model in list(query):
                    add_to_index(index, model, True)
                print("{} done".format(table.__tablename__))
            print("finished in {} seconds".format(time.clock()-started_time))


        except Exception as e:
            raise e
            exit(0)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
