"""
Survey email body type related helper
"""
from flask import current_app

from app.base import constants as APP
from app.common.helpers import generate_event_book_token, \
    generate_event_book_email_link
from app.resources.unsubscriptions.helpers import (
    generate_unsubscribe_email_link)


class LaunchContent(object):
    """
    email contents for survey launch Content
    """

    def __init__(self):
        super(LaunchContent, self).__init__()

    def get_invitee_content(self, invitee_name, survey, invitee, invitee_email):
        """
        generate invitee content
        """
        subject, body, attachment, html = '', '', '', ''
        # token generation
        payload = generate_event_book_token(invitee, APP.EVNT_SURVEY)
        # generate event url for login or registration
        survey_url = generate_event_book_email_link(
            current_app.config['SURVEY_PARTICIPATE_ADD_URL'],
            survey, event_type=APP.EVNT_SURVEY, payload=payload)

        with open('email_html_docs/survey/survey_launch_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(company_name)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += '%(company_name)s is conducting an online perception ' + \
                'survey to understand investor perception about its ' + \
                'offerings and capabilities. \r\n\r\n' + \
                'We invite you to participate in this brief online ' + \
                'survey. All your personal details and specific responses' + \
                ' will be kept confidential. \r\n\r\n'
        body += 'Request you to please complete this brief survey ' + \
                'by clicking the link below. \r\n\r\n'
        body += '%(survey_link)s \r\n\r\n\r\n'
        body += 'Thank you for your participation in advance. \r\n\r\n'
        body += 'Regards, \r\n\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': invitee_name,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': survey.account.account_name,
            'survey_link': survey_url
        }
        html_body_dict = {
            'user_name': invitee_name,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': survey.account.account_name,
            'survey_link': survey_url,
            'unsubscribe': generate_unsubscribe_email_link(invitee_email)
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)
        body = body % body_dict

        return subject, body, attachment, html, invitee_name


class CompletionContent(object):
    """
    email contents for survey completion
    """

    def __init__(self, arg):
        super(CompletionContent, self).__init__()
        self.arg = arg

    def get_responded_content(self, responded_name):
        """
        generate survey responded content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build content
        # with open('email_html_docs/corporate_access_emails/'
        #           'launch_invitee_email.html', 'r') as htmlfile:
        #         htmlfile = htmlfile.read()
        subject = 'Survey is completed'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Survey is completed'
        body += '\r\n\r\n Thanks.'
        html = ''
        body = body % {'user_name': responded_name}
        return subject, body, attachment, html, responded_name
