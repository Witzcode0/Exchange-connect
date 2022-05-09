from flask import current_app
from flask import g, request
from flask_restful import abort
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from app import es, db
from app.global_search import constants as GS
from app.resources.accounts import constants as ACCT
from app.domain_resources.domains.helpers import (
    get_domain_info, get_domain_name)
from app.resources.roles.models import RoleMenuPermission, Role

from queueapp.elastic_search_tasks import (
    update_elastic_document, update_matched_docs)


def add_to_index(index, model, from_script=False, is_update=False):
    """
    Document will be added in elastic search , id will be prepared with the
    format : <table_class_name> + <_> + <row_id>
    e.g : Webinar_101
    If Document with same Id already present it will get updated with
    complete override

    :param index: string, this will be used for _index and _doc_type
    :param model: instance of a table row
    :param from_script: boolean flag to know whether reindexing
        as all data is populated in the db there will be no need of delay for
        indexing
    :param is_update: boolean flag to know if updating a record
    """
    try:
        payload = {}
        row_id = model.row_id
        account_id = None
        corporate_account_id = None
        user_id = None

        model_name = model.__class__.__name__
        if model_name == 'UserSettings':
            update_elastic_document.s(
                model.user_id, 'UserProfile', None,
                None, model.user_id, from_script).delay()
            return True
        for field in model.__global_searchable__:
            payload[field] = getattr(model, field)

        if model_name in ['UserProfile', 'CRMContact']:
            if model_name is 'UserProfile':
                # as changing user profile is done by passing user id and not
                # user profile id
                row_id = model.user_id
                user_id = row_id
            payload['full_name'] = model.first_name + ' ' + model.last_name
            payload['full_name_r'] = model.last_name + ' ' + model.first_name

        if model_name is 'Webinar' and not payload['open_to_account_types']:
            # if open_to_account_types is empty no need to index it
            payload.pop('open_to_account_types')

        if model_name == 'Account':
            # as changing account is done by account_profile_api
            model_name = 'AccountProfile'
            account_profile = get_act_dict(model)
            payload.update(account_profile)
            if is_update:
                state = db.inspect(model)
                for attr in state.attrs:
                    hist = attr.load_history()
                    if not hist.has_changes():
                        continue
                    if attr.key in account_profile:
                        update_matched_docs.s(row_id, account_profile).delay()
                        break

        if hasattr(model, 'account'):
            if model.account:
                account_profile = get_act_dict(model.account)
                payload['account'] = account_profile
            else:
                # account relationship is not yet populated in db
                # so add celery task to update account data
                account_id = model.account_id

        if hasattr(model, 'corporate_account'):
            if model.corporate_account:
                account_profile = get_act_dict(model.corporate_account)
                payload['corporate_account'] = account_profile
            else:
                # corporate_account relationship is not yet populated in db
                # so add celery task to update corporate_account data
                corporate_account_id = model.corporate_account_id

        if model_name == 'CorporateAccessEvent':
            payload['event_type'] = model.event_sub_type.name
        payload['module'] = model_name
        payload['priority'] = GS.MODULE_EXTRAS[model_name]['priority']
        doc_id = model_name + '_' + str(row_id)
        es.index(index=index, doc_type=index, id=doc_id, body=payload)
        if (model_name in ['CorporateAccessEvent', 'Webinar', 'Webcast']
                or any([account_id, corporate_account_id, user_id])):
            update_elastic_document.s(
                row_id, model_name, account_id,
                corporate_account_id, user_id, from_script).delay()

    except Exception as e:
        current_app.logger.exception(e)
        return False


def get_act_dict(account):
    """

    :param account: instance of account model
    :return: account profile dictionary
    """

    account_profile = {}
    sector_name = ''
    industry_name = ''
    if account.profile.sector:
        sector_name = account.profile.sector.name
    if account.profile.industry:
        industry_name = account.profile.industry.name
    account_profile['account_name'] = account.account_name
    account_profile['account_type'] = account.account_type
    account_profile['sector_name'] = sector_name
    account_profile['industry_name'] = industry_name
    account_profile['row_id'] = account.row_id
    account_profile['country'] = account.profile.country
    account_profile['blocked'] = account.blocked
    account_profile['domain_id'] = account.domain_id

    return account_profile


def remove_from_index(index, model):
    """
    Elastic Document Id is derived and the document is deleted from index

    :param index: string, this will be used for _index and _doc_type
    :param model: instance of a table row
    """
    try:
        class_name = model.__class__.__name__
        row_id = model.row_id
        if class_name is 'Account':
            class_name = 'AccountProfile'
        if class_name is 'UserProfile':
            row_id = model.user_id
        doc_id = class_name + '_' + str(row_id)
        es.delete(index=index, doc_type=index, id=doc_id, ignore=[404])

    except Exception as e:
        current_app.logger.exception(e)
        return False


def update_document(index, doc_id, document):
    """
    document will get merged with the existing
    document, i.e. existing key's value will get updated and new key
    will be added
    :param index: string, this will be used for _index and _doc_type
    :param doc_id: string, elastic document id
    :param document: dictionary
    """
    try:
        body = {"doc": document}
        es.update(index=index, doc_type=index, id=doc_id, body=body)

    except Exception as e:
        current_app.logger.exception(e)
        return False


def remove_index(index):
    """
    index will be removed from elastic search

    :param index: string
    """
    try:
        es.indices.delete(index=index, ignore=[400, 404])
    except Exception as e:
        current_app.logger.exception(e)
        return False


def query_index(index, query, main_filter, page=1, per_page=10):
    """
    query will be searched in all the documents with appropriate filter

    :param index: string
    :param query: string
    :param page: int
    :param per_page: int
    :return: dictionary
    """
    result = {
        'total': 0,
        'results': []
    }
    try:
        user_email = g.current_user['email']
        user_id = g.current_user['row_id']
        user_act_type = g.current_user['account_type']
        domain_name = get_domain_name()
        domain_id, domain_config = get_domain_info(domain_name)
        # clause for matching accounts
        account_clause = {
            'bool': {
                'must': {'match_phrase_prefix': {'account_name': query}},
                'filter': {
                    'bool': {
                        'must': [
                            {'term': {'module': 'AccountProfile'}},
                            {'term': {'domain_id': domain_id}},
                            {'term': {'blocked': False}}
                        ],
                        'must_not': [
                            {'term': {'account_type': ACCT.ACCT_ADMIN}},
                            {'term': {'account_type': ACCT.ACCT_GUEST}}
                        ]
                    }
                }

            }
        }

        # clause for matching corporate announcement
        announcement_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'subject': query}},
                    {'match_phrase_prefix': {'description': query}},
                    {'match_phrase_prefix': {'category': query}}
                ],
                'minimum_should_match': 1,
                'filter': [
                    {'term': {'account.domain_id': domain_id}},
                    {'term': {'module': 'CorporateAnnouncement'}},
                    {'term': {'account.blocked': False}}
                ],
            }
        }

        # creator - all matching events owned by a user are included
        # invited user - matching events which are not draft and cancelled
        # matching open events which are not draft and cancelled are included

        event_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'title': query}},
                    {'match_phrase_prefix': {'description': query}}
                ],
                'minimum_should_match': 1,
                'filter': {
                    'bool': {
                        'must': [
                            {'term': {'account.blocked': False}},
                            {'term': {'module': 'CorporateAccessEvent'}},
                            {'term': {'account.domain_id': domain_id}}
                        ],
                        'should': [
                            {'term': {'created_by': user_id}},
                            {'bool': {
                                'must': [
                                    {'term': {'cancelled': False}},
                                    {'term': {'is_draft': False}}
                                ],
                                'should': [
                                    {'term': {'user_emails': user_email}},
                                    {'bool': {
                                        'must': [
                                            {'term': {'open_to_all': True}},
                                            {'term': {
                                                'account_type_preference':
                                                    user_act_type}}]
                                    }},
                                ],
                                'minimum_should_match': 1
                            }},
                        ],
                        'minimum_should_match': 1
                    }
                }
            }
        }

        # matching user profiles (all) and

        user_profile_filters = [
            {'term': {'module': 'UserProfile'}},
            {'term': {'search_privacy': g.current_user['account_type']}},
            {'term': {'account.blocked': False}},
            {'term': {'account.domain_id': domain_id}}
        ]
        sector_id = g.current_user['account_model'].profile.sector_id
        if sector_id:
            user_profile_filters.append({
                'term': {'search_privacy_sector': sector_id}
            })

        industry_id = g.current_user['account_model'].profile.industry_id
        if industry_id:
            user_profile_filters.append({
                'term': {
                    'search_privacy_industry': industry_id}
            })

        market_cap = g.current_user['account_model'].profile.market_cap
        if market_cap:
            user_profile_filters.append({
                'range': {
                    'search_privacy_market_cap_min': {'lte': market_cap}
                }
            })
            user_profile_filters.append({
                'range': {
                    'search_privacy_market_cap_max': {'gte': market_cap}}
            })

        if g.current_user['profile']['designation_link']:
            designation_level = \
                g.current_user['profile']['designation_link']['designation_level']
            user_profile_filters.append({
                'term': {'search_privacy_designation_level': designation_level}
            })

        user_profile_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'first_name': query}},
                    {'match_phrase_prefix': {'last_name': query}},
                    {'match_phrase_prefix': {'full_name': query}},
                    {'match_phrase_prefix': {'full_name_r': query}},
                    {'match_phrase_prefix': {'designation': query}},
                    {'match_phrase_prefix': {'account.account_name': query}},
                ],
                'minimum_should_match': 1,
                'filter': {
                    'bool': {
                        'must': user_profile_filters,
                        'must_not': [
                            {'term':
                                {'_id': 'UserProfile_{}'.format(user_id)}},
                            {'terms':
                                {'account.account_type': [
                                    ACCT.ACCT_ADMIN,  ACCT.ACCT_GUEST]}}
                        ]
                    },
                }
            }
        }

        # matching crm contacts (created by user) are included
        crm_contacts_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'first_name': query}},
                    {'match_phrase_prefix': {'middle_name': query}},
                    {'match_phrase_prefix': {'last_name': query}},
                    {'match_phrase_prefix': {'full_name': query}},
                    {'match_phrase_prefix': {'full_name_r': query}},
                    {'match_phrase_prefix': {'company': query}},
                    {'match_phrase_prefix': {'designation': query}},
                ],
                'minimum_should_match': 1,
                'filter': {
                    'bool': {
                        'must': [
                            {'term': {'module': 'CRMContact'}},
                            {'term': {'created_by': user_id}}
                        ]
                    },
                }
            }
        }

        # creator - all matching webinars owned by a user are included
        # invited user - matching webinars which are not draft and cancelled
        # matching open_to_public webinars or open to account type
        # which are not draft and cancelled  are included
        webinar_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'title': query}},
                    {'match_phrase_prefix': {'description': query}}
                ],
                'minimum_should_match': 1,
                'filter': {
                    'bool': {
                        'must': [
                            {'term': {'account.blocked': False}},
                            {'term': {'module': 'Webinar'}},
                            {'term': {'account.domain_id': domain_id}}
                        ],
                        'should': [
                            {'term': {'created_by': user_id}},
                            {'bool': {
                                'must': [
                                    {'term': {'is_draft': False}},
                                    {'term': {'cancelled': False}},
                                ],
                                'should': [
                                    {'term': {'user_emails': user_email}},
                                    {'term': {'open_to_all': True}},
                                    {'term': {
                                        'open_to_account_types': user_act_type
                                    }},
                                ],
                                'minimum_should_match': 1
                            }},
                        ]
                    }
                }
            }
        }

        # creator - all matching webcasts owned by a user are included
        # invited user - matching webcasts which are not draft and cancelled

        webcast_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'title': query}},
                    {'match_phrase_prefix': {'description': query}}
                ],
                'minimum_should_match': 1,
                'filter': {
                    'bool': {
                        'must': [
                            {'term': {'account.blocked': False}},
                            {'term': {'module': 'Webcast'}},
                            {'term': {'account.domain_id': domain_id}}
                        ],
                        'should': [
                            {'term': {'created_by': user_id}},
                            {'bool': {
                                'must': [
                                    {'term': {'is_draft': False}},
                                    {'term': {'cancelled': False}},
                                    {'term': {'user_emails': user_email}}
                                ]
                            }}
                        ],
                        'minimum_should_match': 1
                    }
                }
            }
        }

        # creator- all matching distribution lists owned by a user are included
        dist_list_clause = {
            'bool': {
                'must': {'match_phrase_prefix': {'campaign_name': query}},
                'filter': {
                    'bool': {
                        'must': [
                            {'term': {'module': 'CRMDistributionList'}},
                            {'term': {'created_by': user_id}}
                        ]
                    }
                }
            }
        }

        # research report
        research_report_clause = {
            'bool': {
                'should': [
                    {'match_phrase_prefix': {'subject': query}},
                    # {'match_phrase_prefix': {'account.account_name': query}},
                ],
                'minimum_should_match': 1,
                'filter': {
                    'term': {'module': 'ResearchReport'}
                }
            }
        }

        filters = {
            GS.ALL: [user_profile_clause, account_clause, announcement_clause,
                     event_clause, crm_contacts_clause, webinar_clause,
                     webcast_clause, dist_list_clause, research_report_clause],
            GS.CAEVENT: [event_clause],
            GS.ACCOUNT: [account_clause],
            GS.ANNOUNCEMENT: [announcement_clause],
            GS.USER_PROFILE: [user_profile_clause],
            GS.CRM_CONTACT: [crm_contacts_clause],
            GS.WEBINAR: [webinar_clause],
            GS.WEBCAST: [webcast_clause],
            GS.CRM_DIST_LIST: [dist_list_clause],
            GS.RESEARCH_REPORT: [research_report_clause],
        }

        permitted_modules = []
        user_menu_codes = []
        perm_menus = RoleMenuPermission.query.filter(and_(
            RoleMenuPermission.role_id==g.current_user['role']['row_id'],
            )).options(joinedload(RoleMenuPermission.menu))
        for each in perm_menus:
            user_menu_codes.append(each.menu.code)
        for module in GS.ALL_MODULES:
            if (module in GS.MODULE_MENUCODE
                and GS.MODULE_MENUCODE[module] not in user_menu_codes):
                continue
            permitted_modules.append(module)

        query = {
            '_source': {
                "excludes": ["user_emails", "priority"],
            },
            'query': {
                'bool': {
                    'should': filters[main_filter],
                    'minimum_should_match': 1,
                    'filter': {
                        "terms": {"module": permitted_modules}
                    }
                },
            },
            'from': (page - 1) * per_page,
            'size': per_page,
            'sort': [{'priority': 'asc'}, '_score']
        }

        search = es.search(index=index, doc_type=index, body=query)
        result['total'] = search['hits']['total']

        for hit in search['hits']['hits']:
            splitted = hit['_id'].split('_')
            row_id = splitted.pop()
            obj = hit['_source']
            obj['row_id'] = int(row_id)
            obj['module_display'] = \
                GS.MODULE_EXTRAS[obj['module']]['display_name']
            result['results'].append(obj)

    except Exception as e:
        current_app.logger.exception(e)
        abort(500)
    return result
