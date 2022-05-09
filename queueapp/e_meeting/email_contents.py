"""
Emeeting email body type related helper
"""

from datetime import datetime as dt

from flask import current_app

from app.common.utils import time_converter
from app.resources.unsubscriptions.helpers import (
    generate_unsubscribe_email_link)


class BaseContentMixin(object):
    def __init__(self, model):
        self.model = model

    def get_logo_url(self):
        """
        Get the logo url from the webinar if not,
        get it from webinar account if not, get default one.
        """
        logo_url = None

            # by super admin only.
        if not logo_url:
            logo_url = self.model.account.profile.profile_photo_url
            if not logo_url:
                self.model.account.profile.load_urls()
                logo_url = self.model.account.profile.profile_photo_url
                if not logo_url:
                    logo_url = current_app.config[
                        'DEFAULT_WN_EVENT_LOGO_URL']
        return logo_url


class LaunchEmeetingContent(BaseContentMixin):
    """
    email contents for e_meeting
    """

    def __init__(self, emeeting):
        super(LaunchEmeetingContent, self).__init__(emeeting)

    def get_invitee_content(self, invitee_name, emeeting, timezone, event_url,
        email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/emeeting/emeeting_launch_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Emeeting %(emeeting)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'You are invited for an e-meeting – ' + \
               ' %(emeeting)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Agenda:\r\n\r\n' + \
               'E-meeting Details:\r\n\r\n' + \
               'Topic/Title: %(emeeting)s\r\n' + \
               'Date:  %(date)s\r\n' + \
               'Time:  %(time)s\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if emeeting.meeting_datetime:
            start_date_obj = time_converter(emeeting.meeting_datetime, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        body_dict = {
            'user_name': invitee_name,
            'emeeting': emeeting.meeting_subject,
            'date': start_date,
            'time': start_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            'link': event_url
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, emeeting, timezone,email,
                            event_url):
        """
        generate creator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/emeeting/emeeting_launch_creator'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Emeeting %(emeeting)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Your e-meeting has been created – ' + \
               ' %(emeeting)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Agenda:\r\n\r\n' + \
               'E-meeting Details:\r\n\r\n' + \
               'Topic/Title: %(emeeting)s\r\n' + \
               'Date:  %(date)s\r\n' + \
               'Time:  %(time)s\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if emeeting.meeting_datetime:
            start_date_obj = time_converter(emeeting.meeting_datetime, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        body_dict = {
            'user_name': creator_name,
            'emeeting': emeeting.meeting_subject,
            'date': start_date,
            'time': start_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            'link': event_url
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, creator_name


class CancellationContent(BaseContentMixin):
    """
    email contents for Emeeting cancellation
    """

    def __init__(self, model):
        super(CancellationContent, self).__init__(model)


    def get_invitee_content(self, invitee_name, emeeting, timezone, event_url,
        email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/emeeting/e_meeting_cancellation'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = 'Event cancelled - %(emeeting)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'The e-meeting you were invited to has been cancelled – ' + \
                '%(emeeting)s. \r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': invitee_name,
            'emeeting': emeeting.meeting_subject,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'link': event_url,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
        }
        html_body_dict = {
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)

        return subject, body, attachment, html, invitee_name


class UpdateContent(BaseContentMixin):
    """
    email contents for Emeeting update
    """

    def __init__(self, model, rescheduled):
        super(UpdateContent, self).__init__(model)
        # self.rescheduled = rescheduled
        self.msg = 'Emeeting - {} details have been updated.'
        self.creator_msg = self.msg
        if rescheduled:
            self.msg = 'The following Emeeting to attend has been rescheduled' \
                  ' – {}.'
            self.creator_msg = 'You have rescheduled the Emeeting – {}.'
        self.msg, self.creator_msg = self.msg.format(model.meeting_subject),\
                                     self.creator_msg.format(model.meeting_subject)

    def get_invitee_content(self, invitee_name, emeeting, timezone, event_url,
        email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/emeeting/emeeting_update_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Emeeting updates for %(emeeting)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'The e-meeting you were invited to has been rescheduled – %(emeeting)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Agenda:\r\n' + \
               'E-meeting Details:\r\n' + \
               'Topic/Title: %(emeeting)s\r\n' + \
               'Date:  %(date)s\r\n' + \
               'Time:  %(time)s\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if emeeting.meeting_datetime:
            start_date_obj = time_converter(emeeting.meeting_datetime, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': invitee_name,
            'emeeting': emeeting.meeting_subject,
            'date': start_date,
            'time': start_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'logo_url': logo_url,
            'link': event_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, emeeting, timezone, email,
                            event_url):
        """
        generate creator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/emeeting/emeeting_update'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Emeeting updates for %(emeeting)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'The e-meeting you were invited to has been rescheduled – %(emeeting)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Agenda:\r\n' + \
               'E-meeting Details:\r\n' + \
               'Topic/Title: %(emeeting)s\r\n' + \
               'Date:  %(date)s\r\n' + \
               'Time:  %(time)s\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if emeeting.meeting_datetime:
            start_date_obj = time_converter(emeeting.meeting_datetime, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': creator_name,
            'emeeting': emeeting.meeting_subject,
            'date': start_date,
            'time': start_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'logo_url': logo_url,
            'link': event_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, creator_name
