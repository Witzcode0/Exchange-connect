"""
Webinar email body type related helper
"""

from datetime import datetime as dt

from flask import current_app

from app.common.utils import time_converter
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
        for host in self.model.webinar_hosts:
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
        for pr in sorted(
                self.model.webinar_participants,
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
        if email is not '':
            email = email[2:]
        if contact_person != '':
            contact_person = contact_person[2:]
            self.rsvp_block_style = ""
        return contact_person, email, contact_number

    def get_logo_url(self):
        """
        Get the logo url from the webinar if not,
        get it from webinar account if not, get default one.
        """
        logo_url = self.model.invite_logo_url
        if not logo_url:
            self.model.load_urls()
            logo_url = self.model.invite_logo_url
            # #TODO may be removed in future, because webinar is created
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


class LaunchContent(BaseContentMixin):
    """
    email contents for Webinar launch
    """

    def __init__(self, webinar):
        super(LaunchContent, self).__init__(webinar)

    def get_invitee_content(self, invitee_name, webinar, timezone, event_url,
        email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_launch_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'You have been invited for the webinar –' + \
               ' %(webinar)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please click on the below link to login or register:\r\n'
        body += '%(link)s\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': invitee_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'link': event_url,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'contact_number': self.contact_number,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, webinar, timezone,email,
                            event_url):
        """
        generate creator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_launch_creator_participant'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Your webinar has been created – ' + \
               ' Topic for the event is %(webinar)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': creator_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'link': event_url
        }
        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'contact_number': self.contact_number,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)

        return subject, body, attachment, html, creator_name

    def get_host_content(
            self, host_name, webinar, timezone, email, event_url):
        """
        generate host content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_launch_host'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Greeting from %(brand_name)s.\r\n' + \
               'You have been designated as host by %(creator_name)s, ' + \
               'for %(webinar)s.\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': host_name,
            'webinar': webinar.title,
            'creator_name': webinar.creator.profile.first_name,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'link': event_url,
        }

        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'contact_number': self.contact_number,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)

        return subject, body, attachment, html, host_name

    def get_participant_content(
            self, participant_name, webinar, timezone, email, event_url):
        """
        generate participant content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_launch_creator_participant'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Your webinar has been created – ' + \
               ' Topic for the event is %(webinar)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': participant_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'link': event_url
        }

        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'contact_number': self.contact_number,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, participant_name

    def get_rsvp_content(self, rsvp_name, webinar, timezone, email, event_url):
        """
        generate rsvp content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_launch_rsvp'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'You have been invited for the webinar –' + \
               ' %(webinar)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        contact_person = ''
        email = ''
        contact_number = ''
        if webinar.rsvps:
            for rsvp in sorted(webinar.rsvps, key=lambda x: (x.sequence_id)):
                if rsvp.contact_person:
                    contact_person += ', ' + rsvp.contact_person
                if rsvp.email:
                    email += ', ' + rsvp.email
                if rsvp.phone:
                    contact_number = rsvp.phone
        if email is not '':
            email = email[2:]
        if contact_person is not '':
            contact_person = contact_person[2:]

        body_dict = {
            'user_name': rsvp_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': contact_person,
            'email': email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'link': event_url
        }
        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'contact_number': contact_number,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, rsvp_name


class CompletionContent(object):
    """
    email contents for webinar completion
    """

    def __init__(self):
        super(CompletionContent, self).__init__()

    def get_attendee_content(self, attendee_name, webinar, email):
        """
        generate attendee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_completion.html',
                  'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s – Thank you for attending %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'We would like to thank you for attending ' + \
                'our %(webinar)s \r\n\r\n.'
        body += ' Hope you enjoyed the \r\n'
        body += 'experience and we look forward to see you at ' + \
                'the next webinar. \r\n\r\n'
        body += 'We truly appreciate your support. ' + \
                'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': attendee_name,
            'webinar': webinar.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'logo_url': logo_url,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict
        return subject, body, attachment, html, attendee_name

    def get_participant_content(self, participant_name, webinar, email):
        """
        generate participant content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_completion.html',
                  'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s – Thank you for attending %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'We would like to thank you for attending ' + \
                'our %(webinar)s.'
        body += ' Hope you enjoyed the \r\n'
        body += 'experience and we look forward to seeing you at ' + \
                'the next webinar. \r\n\r\n'
        body += 'We truly appreciate your support. ' + \
                'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': participant_name,
            'webinar': webinar.title,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'logo_url': logo_url,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body % body_dict
        return subject, body, attachment, html, participant_name


class UpdateContent(BaseContentMixin):
    """
    email contents for Webinar update
    """

    def __init__(self, model, rescheduled):
        super(UpdateContent, self).__init__(model)
        # self.rescheduled = rescheduled
        self.msg = 'Webinar - {} details have been updated.'
        self.creator_msg = self.msg
        if rescheduled:
            self.msg = 'The following webinar to attend has been rescheduled' \
                  ' – {}.'
            self.creator_msg = 'You have rescheduled the webinar – {}.'
        self.msg, self.creator_msg = self.msg.format(model.title),\
                                     self.creator_msg.format(model.title)

    def get_invitee_content(self, invitee_name, webinar, timezone, event_url,
        email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_update_invitee'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar updates for %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s \r\n' + \
               'Webinar - %(webinar)s details have been updated.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please click on the below link to login or register:\r\n'
        body += '%(link)s\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': invitee_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'link': event_url,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'msg': self.msg
        }
        html_body_dict = {
            'speaker_list': self.speaker_list_html,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, webinar, timezone, email,
                            event_url):
        """
        generate creator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_update'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar updates for %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s \r\n' + \
               'Webinar - %(webinar)s details have been updated.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': creator_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'msg': self.creator_msg,
            'link': event_url
        }
        html_body_dict = {
            'speaker_list': self.speaker_list_html,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, creator_name

    def get_host_content(
            self, host_name, webinar, timezone, email, event_url):
        """
        generate host content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_update'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar updates for %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s \r\n' + \
               'Webinar - %(webinar)s details have been updated.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': host_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'msg': self.msg,
            'link': event_url
        }
        html_body_dict = {
            'speaker_list': self.speaker_list_html,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, host_name

    def get_participant_content(
            self, participant_name, webinar, timezone, email, event_url):
        """
        generate participant content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_update'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar updates for %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s \r\n' + \
               'Webinar - %(webinar)s details have been updated.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': participant_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'msg': self.msg,
            'link': event_url
        }
        html_body_dict = {
            'speaker_list': self.speaker_list_html,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, participant_name

    def get_rsvp_content(self, rsvp_name, webinar, timezone, email, event_url):
        """
        generate rsvp content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_update'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar updates for %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'Thanks for choosing %(brand_name)s \r\n' + \
               'Webinar - %(webinar)s details have been updated.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': rsvp_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'msg': self.msg,
            'link': event_url
        }
        html_body_dict = {
            'speaker_list': self.speaker_list_html,
            'participant_list': self.participant_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, rsvp_name


class RegisterContent(BaseContentMixin):
    """
    email contents for Webinar register
    """

    def __init__(self, model):
        super(RegisterContent, self).__init__(model)

    def get_invitee_content(self, invitee_name, webinar, timezone,
                            conference_url, email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_register'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'You have been successfully registered for the webinar –' + \
               ' %(webinar)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')

        body_dict = {
            'user_name': invitee_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'contact_number': self.contact_number,
            'participant_list': self.participant_html,
            'conference_url': conference_url,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name


class CancellationContent(BaseContentMixin):
    """
    email contents for Webinar cancellation
    """

    def __init__(self, model):
        super(CancellationContent, self).__init__(model)


    def get_invitee_content(self, invitee_name, webinar, timezone, event_url,
        email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_cancellation'
                  '.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = 'Event cancelled - %(webinar)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'We regret to inform that the ' + \
                '%(webinar)s has been cancelled. ' + \
                'Thank You for showing interest in the event.\r\n\r\n'
        body += 'Event Details \r\n\r\n'
        body += 'Status: Cancelled \r\n'
        body += 'Webinar: %(webinar)s\r\n'
        body += 'Day & Date: %(date_time)s\r\n'
        body += 'Host: %(speaker_list)s\r\n\r\n'
        body += 'To find details of the upcoming events please click' + \
                ' on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time = '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        body_dict = {
            'user_name': invitee_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'link': event_url,
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
        }
        html_body_dict = {
            'speaker_list': self.speaker_list_html,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)

        return subject, body, attachment, html, invitee_name


class ReminderContent(BaseContentMixin):
    """
    email contents for Webinar reminder
    """

    def __init__(self, model):
        super(ReminderContent, self).__init__(model)


    def get_invitee_content(self, invitee_name, webinar, timezone,
                            conference_url, event_url, email):
        """
        generate invitee content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        logo_url = self.get_logo_url()

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/webinar/webinar_reminder_email.html', 'r'
                  ) as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = 'Reminder: %(brand_name)s - Webinar %(webinar)s.'
        body = 'Hi %(user_name)s, \r\n\r\n' + \
               'This is a reminder that %(webinar)s will begin in ' \
               ' %(date_time)s.' + \
               '\r\n' + \
               'Please find the event details below:\r\n\r\n' + \
               'Topic/Title: %(webinar)s\r\n' + \
               'Date & Time:  %(date_time)s\r\n' + \
               'Contributors:  %(participant_list)s\r\n' + \
               'Speakers:  %(speaker_list)s\r\n' + \
               'Contact Person: %(contact_person)s\r\n' + \
               'Contact Email: %(email)s\r\n\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, reminder_time = '', '', ''
        if webinar.started_at:
            start_date_obj = time_converter(webinar.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
            latest_time = time_converter(dt.utcnow(), to=timezone)
            diff_time = start_date_obj - latest_time
            reminder_time = int((diff_time.total_seconds())/60/60)
        button_label = 'Go to Webinar'
        if not conference_url:
            conference_url = event_url
            button_label = 'Book Now'

        body_dict = {
            'user_name': invitee_name,
            'webinar': webinar.title,
            'date_time': start_date + ' ' + start_time,
            'speaker_list': self.speaker_list,
            'contact_person': self.contact_person,
            'email': self.contact_email,
            'participant_list': self.participant,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME']
        }
        html_body_dict = {
            'date': start_date,
            'time': start_time,
            'speaker_list': self.speaker_list_html,
            'contact_number': self.contact_number,
            'participant_list': self.participant_html,
            'conference_url': conference_url,
            'button_label': button_label,
            'logo_url': logo_url,
            'unsubscribe': unsubscribe_url,
            "rsvp_block_style": self.rsvp_block_style
        }
        subject = subject % body_dict
        body = body % body_dict
        body_dict.update(html_body_dict)
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name
