"""
Webcast email body type related helper
"""

from datetime import datetime as dt

from flask import current_app

from app.common.utils import time_converter
from app.base import constants as APP
from app.common.helpers import generate_event_book_token, \
    generate_event_book_email_link
from app.resources.unsubscriptions.helpers import (
    generate_unsubscribe_email_link)


class BaseContentMixin(object):
    def __init__(self, model):
        self.model = model
        self.speaker_list, self.speaker_list_html = self.get_host_list()
        self.participant, self.participant_html = self.get_participant_list()
        self.contact_person, self.contact_email, self.contact_number = \
            self.get_rsvp_list()

    def get_host_list(self):
        hosts = ''
        hosts_html = ''
        for host in self.model.external_hosts:
            fn = host.host_first_name
            ln = host.host_last_name
            des = host.host_designation or ''
            if host.host_id:
                fn = host.host.profile.first_name
                ln = host.host.profile.last_name
                des = host.host.profile.designation
            hosts += fn + ' ' + ln
            hosts_html += '<p>' + fn + ' ' + ln + '<br>'
            if des:
                hosts += '-' + des
                hosts_html += '<small>' + des + '</small>'

            hosts += ', '
            hosts_html += '</p>'
        if hosts_html:
            hosts_html = '<strong>Hosts</strong>' + \
                               hosts_html
        return hosts[:-2], hosts_html

    def get_participant_list(self):
        participant, participant_html = '', ''
        if self.model.webcast_participants:
            for pr in sorted(
                    self.model.webcast_participants,
                    key=lambda x: x.sequence_id):
                fn = pr.participant_first_name
                ln = pr.participant_last_name
                des = pr.participant_designation or ''

                if pr.participant_id:
                    fn = pr.participant.profile.first_name
                    ln = pr.participant.profile.last_name
                    des = pr.participant.profile.designation
                participant += fn + ' ' + ln
                participant_html += '<p>' + fn + ' ' + ln + '<br>'
                if des:
                    participant += '-' + des
                    participant_html += '<small>' + des + '</small>'
                participant += ', '
                participant_html += '</p>'
        if participant_html:
            participant_html = '<strong>Participants</strong>' + \
                               participant_html

        return participant[:-2], participant_html

    def get_rsvp_list(self):
        contact_person = ''
        email = ''
        contact_number = ''
        self.rsvp_block_style = "display:none;"
        if self.model.rsvps:
            for rsvp in sorted(self.model.rsvps, key=lambda x: (x.sequence_id)):
                if rsvp.contact_person:
                    contact_person += ', ' + rsvp.contact_person
                if rsvp.email:
                    email += ', ' + rsvp.email
                if rsvp.phone:
                    contact_number = rsvp.phone
        if email != '':
            email = email[2:]
        if contact_person != '':
            contact_person = contact_person[2:]
            self.rsvp_block_style = ""
        return contact_person, email, contact_number

class LaunchContent(BaseContentMixin):
    """
    email contents for webcast launch Content
    """

    def __init__(self, model):
        super(LaunchContent, self).__init__(model)

    def get_logo_url(self, webcast):
        """
        Get the logo url from the webcast if not,
        get it from webcast account if not, get default one.
        """
        logo_url = webcast.invite_logo_url
        if not logo_url:
            webcast.load_urls()
            logo_url = webcast.invite_logo_url
            if not logo_url:
                logo_url = webcast.account.profile.profile_photo_url
                if not logo_url:
                    webcast.account.profile.load_urls()
                    logo_url = webcast.account.profile.profile_photo_url
                    if not logo_url:
                        logo_url = current_app.config[
                            'DEFAULT_WC_EVENT_LOGO_URL']

        return logo_url

    def get_invitee_content(self, invitee_name, webcast, timezone, invitee,
                            email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url(webcast)
        # token generation
        payload = generate_event_book_token(invitee, APP.EVNT_WEBCAST)
        # generate event url for login or registration
        event_url = generate_event_book_email_link(
            current_app.config['WEBCAST_EVENT_JOIN_ADD_URL'],
            webcast, payload=payload)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_launch_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - %(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'You have been invited for the webcast – ' + \
               ' %(webcast)s of %(company_name)s.' + \
               '\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please click on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': invitee_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'brand_name': current_app.config['BRAND_NAME'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'link': event_url,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            'rsvp_block_style': self.rsvp_block_style}
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, webcast, timezone, email):
        """
        generate creator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_launch_creator_participant'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - %(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Your webcast has been created – ' + \
               ' %(webcast)s of %(company_name)s.' + \
               '\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p')

        body_dict = {
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': creator_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            'rsvp_block_style': self.rsvp_block_style
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, creator_name

    def get_host_content(self, host_name, webcast, timezone, host_email):
        """
        generate host content
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_launch_host'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - %(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Greeting from %(brand_name)s.\r\n' + \
               'You have been designated as host by %(creator_name)s, ' + \
               'for %(webcast)s of %(company_name)s.\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p') or ''

        body_dict = {
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': host_name,
            'webcast': webcast.title,
            'creator_name': webcast.creator.profile.first_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(host_email),
            'rsvp_block_style': self.rsvp_block_style
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict
        return subject, body, attachment, html, host_name

    def get_participant_content(self, participant_name, webcast, timezone,
                                participant_email):
        """
        generate participant content
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_launch_creator_participant'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - %(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Your webcast has been created – ' + \
               ' %(webcast)s of %(company_name)s.' + \
               '\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p') or ''

        body_dict = {
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': participant_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(participant_email),
            'rsvp_block_style': self.rsvp_block_style
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict
        return subject, body, attachment, html, participant_name

    def get_rsvp_content(self, rsvp_name, webcast, rsvp_email):
        """
        generate rsvp content
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_launch_rsvp'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - %(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'You have been invited for the webcast – ' + \
               ' %(webcast)s of %(company_name)s.' + \
               '\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at)
            end_time = dt.strftime(end_date_obj, '%I:%M %p')

        body_dict = {
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': rsvp_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(rsvp_email),
            'rsvp_block_style': self.rsvp_block_style
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, rsvp_name


class CompletionContent(object):
    """
    email contents for webcast completion
    """

    def __init__(self):
        super(CompletionContent, self).__init__()

    def get_logo_url(self, webcast):
        """
        Get the logo url from webcast if not, get it from webcast account
        """
        logo_url = webcast.invite_logo_url
        if not logo_url:
            webcast.load_urls()
            logo_url = webcast.invite_logo_url
            if not logo_url:
                logo_url = webcast.account.profile.profile_photo_url
                if not logo_url:
                    webcast.account.profile.load_urls()
                    logo_url = webcast.account.profile.profile_photo_url

        return logo_url

    def get_attendee_content(self, attendee_name, webcast, attendee_email):
        """
        generate attendee content
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        htmlfile = ''
        with open('email_html_docs/webcast/webcast_completion.html', 'r'
                  ) as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s – Thank you for attending %(webcast)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += '%(company_name)s would like to thank you for attending ' + \
                'our %(webcast)s \r\n\r\n.'
        body += 'Hope you enjoyed the \r\n\r\n'
        body += 'experience and we look forward to see you at ' + \
                'the next Webcast. \r\n\r\n'
        body += 'We truly appreciate your support. Please let us know ' + \
                'if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': attendee_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'brand_name': current_app.config['BRAND_NAME'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(attendee_email)
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, attendee_name

    def get_participant_content(self, participant_name, webcast,
            participant_email):
        """
        generate participant content
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        htmlfile = ''
        with open('email_html_docs/webcast/webcast_completion.html', 'r'
                  ) as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s – Thank you for attending %(webcast)s,'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += '%(company_name)s would like to thank you for attending ' + \
                'our %(webcast)s.'
        body += 'Hope you enjoyed the \r\n\r\n'
        body += 'experience and we look forward to see you at ' + \
                'the next Webcast. \r\n\r\n'
        body += 'We truly appreciate your support. Please let us know ' + \
                'if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': participant_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'brand_name': current_app.config['BRAND_NAME'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(participant_email)
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, participant_name


class UpdateContent(BaseContentMixin):
    """
    email contents for webcast update
    """

    def __init__(self, model):
        super(UpdateContent, self).__init__(model)

    def get_logo_url(self, webcast):
        """
        Get the logo url from webcast if not, get it from webcast account
        """
        logo_url = webcast.invite_logo_url
        if not logo_url:
            webcast.load_urls()
            logo_url = webcast.invite_logo_url
            if not logo_url:
                logo_url = webcast.account.profile.profile_photo_url
                if not logo_url:
                    webcast.account.profile.load_urls()
                    logo_url = webcast.account.profile.profile_photo_url

        return logo_url

    def get_content(self, name, webcast, timezone, e_mail):
        """
        generate update content for creators, rsvps, hosts and participants
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_update'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webcast updates for ' +\
                  '%(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s' + \
               ' %(webcast)s %(company_name)s details have been ' + \
               'updated.\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'brand_name': current_app.config['BRAND_NAME'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(e_mail),
            'rsvp_block_style': self.rsvp_block_style
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, name

    def get_invitee_content(self, invitee_name, webcast, timezone, event_url,
                            invitee_email):
        """
        generate update content for invitees
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_update_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webcast updates for ' +\
                  '%(company_name)s %(webcast)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s' + \
               ' %(webcast)s %(company_name)s details have been ' + \
               'updated.\r\n' + \
               'Please find the webcast details below:\r\n\r\n' + \
               'Company Name: %(company_name)s\r\n' + \
               'Webcast: %(webcast)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please click on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': invitee_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'brand_name': current_app.config['BRAND_NAME'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'participant_html': self.participant_html,
            'link': event_url,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(invitee_email),
            'rsvp_block_style': self.rsvp_block_style
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, invitee_name


class CancellationContent(BaseContentMixin):
    """
    email contents for webcast cancellation
    """

    def __init__(self, model):
        super(CancellationContent, self).__init__(model)

    def get_logo_url(self, webcast):
        """
        Get the logo url from webcast if not, get it from webcast account
        """
        logo_url = webcast.invite_logo_url
        if not logo_url:
            webcast.load_urls()
            logo_url = webcast.invite_logo_url
            if not logo_url:
                logo_url = webcast.account.profile.profile_photo_url
                if not logo_url:
                    webcast.account.profile.load_urls()
                    logo_url = webcast.account.profile.profile_photo_url
                    if not logo_url:
                        logo_url = current_app.config[
                            'DEFAULT_WC_EVENT_LOGO_URL']

        return logo_url

    def get_invitee_content(self, invitee_name, webcast, timezone, event_url,
                            invitee_email):
        """
        generate cancellation content for invitees
        """
        logo_url = self.get_logo_url(webcast)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webcast/webcast_cancelled'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = 'Webcast cancelled - %(webcast)s of %(company_name)s'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'We regret to inform that the %(webcast)s of ' + \
               '%(company_name)s has been cancelled. Thank You for ' + \
               'showing interest in the event.\r\n' + \
               'Event Details:\r\n\r\n' + \
               'Status: Cancelled\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Host:  %(speaker_list)s\r\n'
        body += 'To find details of the upcoming events please click on ' + \
                'the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_time = '', '', ''
        if webcast.started_at:
            start_date_obj = time_converter(webcast.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if webcast.ended_at:
            end_date_obj = time_converter(webcast.ended_at, to=timezone)
            end_time = dt.strftime(end_date_obj, '%I:%M %p')
        body_dict = {
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': invitee_name,
            'webcast': webcast.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': webcast.account.account_name,
            'date_time': start_date + ' ' + start_time + ' - ' + end_time,
            'speaker_list': self.speaker_list,
            'speaker_list_html': self.speaker_list_html,
            'link': event_url,
            'logo_url': logo_url,
            'unsubscribe': generate_unsubscribe_email_link(invitee_email)
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict

        return subject, body, attachment, html, invitee_name
