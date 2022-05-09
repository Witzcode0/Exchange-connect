"""
The base task queue
"""

# from celery.task import current
from celery.utils.log import get_task_logger

from app import flaskapp, make_celery
from app.common.utils import send_email
from app.base import constants as APP


celery_app = make_celery(flaskapp)
logger = get_task_logger(__name__)


def send_email_actual(*args, **kwargs):
    """
    In order to avoid tasks calling other tasks, this function does the actual
    email sending.
    """

    # keep getting different kinds of signature errors, hence using this,
    # instead of args/kwargs on definition
    raise_ex = kwargs.pop('raise_ex', False)
    force_email = kwargs.pop('force_email', False)
    try:
        email_type = kwargs.pop('email_type', '')
        # #TODO: generate email according to email_type

        subject = kwargs.pop('subject', '')
        keywords = kwargs.pop('keywords', '')
        from_name = kwargs.pop('from_name', '')
        from_email = kwargs.pop('from_email', '')
        to_addresses = kwargs.pop('to_addresses', [])
        cc_addresses = kwargs.pop('cc_addresses', [])
        bcc_addresses = kwargs.pop('bcc_addresses', [])
        reply_to = kwargs.pop('reply_to', '')
        body = kwargs.pop('body', '').encode('utf8')
        html = kwargs.pop('html', '').encode('utf8')
        attachment = kwargs.pop('attachment', '')
        smtp_settings = kwargs.pop('smtp_settings', {})
        ics_file = kwargs.pop('ics_file', None)

        to_addresses = list(filter(None, to_addresses))
        params = {'username': flaskapp.config['SMTP_USERNAME'],
                  'password': flaskapp.config['SMTP_PASSWORD'],
                  'smtphost': flaskapp.config['SMTP_HOST'],
                  'from_name': from_name, 'from_email': from_email,
                  'reply_to': reply_to, 'to_addresses': to_addresses,
                  'cc_addresses': cc_addresses, 'bcc_addresses': bcc_addresses,
                  'body': body, 'subject': subject, 'html': html, 'keywords':keywords,
                  'attachment': attachment, 'ics_file': ics_file}
        if smtp_settings:
            # existing keys of params will be overridden by smtp_settings
            # others will be kept as it is.
            params = {**params, **smtp_settings}

        if not flaskapp.config['DEBUG'] or force_email:
            send_email(**params)
            sent_addresses = ','.join(['"' + addr + '"'
                                       for addr in to_addresses + cc_addresses
                                       + bcc_addresses])
            logger.info('sent email="' + email_type + '" to emails=' +
                        sent_addresses)
    except Exception as e:
        logger.exception(args)
        if raise_ex:
            raise e
        # log e
        logger.exception('Error in sending mail')


def send_error_email_from_tasks(e, force=False):
    """
    Sends error email to admin.
    """

    if flaskapp.config['DEBUG'] and not force:
        return
    """send_email_actual(
        email_type='Error', body=e, force_email=force,
        keywords=APP.ERROR_EMAIL,
        subject='Error occurred', to_addresses=flaskapp.config[
            'DEVELOPER_EMAILS'],
        from_email=flaskapp.config['DEFAULT_SENDER_EMAIL'],
        from_name=flaskapp.config['DEFAULT_SENDER_NAME'])"""
    return


@celery_app.task(bind=True, ignore_result=True)
def send_email_task(self, email_type, *args, **kwargs):
    """
    Task for sending emails.
    """

    log_uid = str(kwargs.pop('log_uid', -1))
    try:
        if email_type == 'error':
            send_error_email_from_tasks(e=kwargs.pop('e', ''))
        else:
            send_email_actual(email_type=email_type, raise_ex=True, *args,
                              **kwargs)
    except Exception as e:
        # log e
        logger.exception(e)
        logger.exception('log_uid=' + log_uid)
        logger.exception('Error in sending mail, retrying...')
        # and retry
        raise self.retry(exc=e)
