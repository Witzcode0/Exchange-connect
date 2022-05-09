"""
    helper functions related to "domain" package.
"""
from functools import lru_cache
from flask import request, current_app

from app import c_abort
from app.domain_resources.domains.models import Domain


def get_domain_name(code=None):
    if code:
        return Domain.query.filter(Domain.code == code).first().name
    if request.user_agent.platform \
            in current_app.config['REQUEST_MOBILE_PLATFORMS']:
        return Domain.query.get(1).name

    if 'Origin' in request.headers:
        return ".".join(
            request.headers['Origin'].split(":")[1].split('.')[1:])
    else:
        return Domain.query.get(1).name


@lru_cache(maxsize=10)
def get_domain_info(domain_name):
    """
    caching to avoid database calls
    :param domain_name: str
    :return: dict of domain info
    """
    domain = Domain.query.filter_by(name=domain_name).first()
    if not domain:
        c_abort(422, message="domain - {} not found".format(domain_name))
    config = {}
    for con in domain.domain_configs:
        config[con.name] = con.value
    return domain.row_id, config
