
from geolite2 import geolite2

from app import db
from app.resources.login_logs.models import LoginLog
from app.common.utils import get_dict_value


def insert_login_log(request, user):
    user_agent = request.user_agent
    data = dict()
    data['user_id'] = user.row_id
    data['domain_id'] = user.account.domain_id
    data['ip'] = request.remote_addr
    data['browser'] = user_agent.browser
    data['platform'] = user_agent.platform
    data['browser_version'] = user_agent.version
    data['device'] = 'Mobile' if 'mobile' in str(user_agent) else 'Desktop'
    reader = geolite2.reader()
    ip_info = reader.get(request.remote_addr)
    geolite2.close()
    if ip_info:
        data['continent_code'] = get_dict_value(ip_info, ['continent','code'])
        data['continent'] = get_dict_value(
            ip_info, ['continent', 'names', 'en'])
        data['country_code'] = get_dict_value(ip_info, ['country', 'iso_code'])
        data['country'] = get_dict_value(ip_info, ['country', 'names', 'en'])
        data['region_code'] = get_dict_value(
            ip_info, ['subdivisions', 0, 'iso_code'])
        data['region'] = get_dict_value(
            ip_info, ['subdivisions', 0, 'names', 'en'])
        data['location'] = get_dict_value(ip_info, ['location'])
        data['city'] = get_dict_value(ip_info, ['city', 'names', 'en'])
        data['postal_code'] = get_dict_value(ip_info, ['postal', 'code'])

    log = LoginLog(**data)
    db.session.add(log)
    db.session.commit()
    return log.row_id


