"""
Corporate access email body type related helper
"""

import os
import requests

from datetime import datetime as dt

from flask import current_app

from app.common.utils import time_converter
from app.base import constants as APP
from app.common.helpers import generate_event_book_token, \
    generate_event_book_email_link
from app.resources.unsubscriptions.helpers import \
    generate_unsubscribe_email_link


class BaseContentMixin(object):
    """
    A base mixin class with common functionality for email content building.
    """

    model = None  # the event object for which email is being generated
    logo_url = None  # the event's invite logo url
    attachment = None  # any attachment during sending invite
    agendas = None  # any agendas for the event
    host = None  # hosts list(for text email)
    show_host_list = None  # hosts list(for html email)
    participant = None  # participants list(for text email)
    show_participant_list = None  # participants list(for html email)
    show_rsvp_list = None  # rsvps(contact person, email) list(for html email)
    contact_person = None  # contact persons for the event(for text email)
    contact_email = None  # contact emails for the event(for text email)
    dial_in_detail = None  # dial in details(for text email)
    alternative_dial_in_detail = None  # alt dial in details(for text email)
    dial_in_detail_html = None  # dial in details(for text email)
    alternative_dial_in_detail_html = None  # alt dial in details(for html)
    venue = None  # the event's venue(for text email)
    venue_html = None  # the event's venue(for html)

    def __init__(self, model):
        super(BaseContentMixin, self).__init__()
        self.model = model

    def get_logo_url(self):
        """
        Get the logo url from the event if not,
        get it from event account if not, get default one.
        """
        logo_url = self.model.invite_logo_url
        if not logo_url:
            self.model.load_urls()
            logo_url = self.model.invite_logo_url
            if not logo_url:
                logo_url = self.model.account.profile.profile_photo_url
                if not logo_url:
                    self.model.account.profile.load_urls()
                    logo_url = self.model.account.profile.profile_photo_url
                    if not logo_url:
                        logo_url = current_app.config[
                            'DEFAULT_CA_EVENT_LOGO_URL']

        return logo_url

    def get_attachment_file(self):
        """
        Get filename from CAEvent attachment
        """
        attachment = ''
        if self.model.attachment:
            self.model.load_urls()
            attachment_url = self.model.attachment_url
            response = requests.get(attachment_url)
            file = os.path.join(
                current_app.config['BASE_DOWNLOADS_FOLDER'],
                self.model.attachment)
            with open(file, 'wb') as f:
                f.write(response.content)
                attachment = file
        return attachment

    def get_agenda_data(self, timezone):
        """
        Get agenda data
        """
        show_agenda, agenda_list, agenda_body = '', '', ''
        agenda_start_time, agenda_end_time = '', ''
        if self.model.event_sub_type.has_slots is False:
            if self.agendas:
                show_agenda = 'Agenda'
                pre_agenda_code = '<tr><td style="padding: 10px;' + \
                    'padding-top: 0px;"><table width="560px"' + \
                    ' style="border:' + \
                    '1px solid #870d14; padding: 10px; text-align: ' + \
                    'center; ">' + \
                    '<tbody><tr><td colspan="3" align="center"><strong>' + \
                    show_agenda + '</strong></td></tr><tr><td>'
                for agenda in self.agendas:
                    if agenda.started_at:
                        start_date_obj = time_converter(
                            agenda.started_at, to=timezone)
                        agenda_start_time = dt.strftime(
                            start_date_obj, '%I:%M %p')
                    if agenda.ended_at:
                        end_date_obj = time_converter(
                            agenda.ended_at, to=timezone)
                        agenda_end_time = dt.strftime(
                            end_date_obj, '%I:%M %p')
                    agenda_list = agenda_list + \
                        (agenda.title if agenda.title else '') + ' - ' + \
                        (agenda.address if agenda.address else '') + ', ' + \
                        (agenda_start_time) + ' - ' + (agenda_end_time) + \
                        '<br>' + \
                        (agenda.description if agenda.description else '') + \
                        '<br><br>'
                    agenda_body = agenda_body + \
                        (agenda.title if agenda.title else '') + ' - ' + \
                        (agenda.address if agenda.address else '') + ', ' + \
                        (agenda_start_time) + ' - ' + (agenda_end_time) + \
                        ', ' + \
                        (agenda.description if agenda.description else '') + \
                        '\n'
                post_agenda_code = '</td></tr></tbody></table></td></tr>'
                agenda_list = pre_agenda_code + agenda_list + post_agenda_code
        return agenda_list, agenda_body

    def get_hosts(self):
        """
        get speaker(host) data
        """
        show_hosts, html_host_list = '', ''
        host = ''
        host_html = ''
        # for hosts display hosts
        if self.model.corporate_access_event_hosts:
            show_hosts = 'Hosts'
            for hst in self.model.corporate_access_event_hosts:
                if hst.host_id:
                    host = (
                        host + hst.host.profile.first_name + ' ' +
                        hst.host.profile.last_name + '-' +
                        (hst.host.profile.designation if
                         hst.host.profile.designation else '') + ', ')
                    host_html = (
                        host_html + '<p>' +
                        (hst.host.profile.first_name if
                         hst.host.profile.first_name else '') + ' ' +
                        (hst.host.profile.last_name if
                         hst.host.profile.last_name else '') +
                        '<br><small>' +
                        (hst.host.profile.designation if
                         hst.host.profile.designation else '') +
                        '</small></p>'
                    )
                else:
                    host = (
                        host + hst.host_first_name + ' ' +
                        hst.host_last_name + ', ')
                    host_html = (
                        host_html + '<p>' +
                        (hst.host_first_name if hst.host_first_name
                         else '') + ' ' +
                        (hst.host_last_name if
                         hst.host_last_name else '') + '<br><small>' +
                        (hst.host_designation if
                         hst.host_designation else '') + '</small></p>')
            html_host_list = host_html
        show_host_list = '<tr><td align="center"><strong>' + \
            show_hosts + '</strong>' + html_host_list + \
            '<br/></td></tr>'
        host = host[:-2]

        return host, show_host_list

    def get_participants(self):
        """
        Get participant data
        """
        show_participants, show_participant_list = '', ''
        participant, participant_html = '', ''
        # for participant, display participant according sequence id
        if self.model.corporate_access_event_participants:
            show_participants = 'Participants'
            for pr in sorted(self.model.corporate_access_event_participants,
                             key=lambda x: (x.sequence_id)):
                if pr.participant_id:
                    participant = (
                        participant + pr.participant.profile.first_name + ' ' +
                        pr.participant.profile.last_name) + ' - ' + \
                        (pr.participant.profile.designation if
                            pr.participant.profile.designation else '') + ', '
                    participant_html = (
                        participant_html + '<p>' +
                        (pr.participant.profile.first_name if
                         pr.participant.profile.first_name else '') + ' ' +
                        (pr.participant.profile.last_name if
                         pr.participant.profile.last_name else '') +
                        '<br><small>' +
                        (pr.participant.profile.designation if
                         pr.participant.profile.designation else '') +
                        '</small></p>')
                else:
                    participant = (
                        participant + pr.participant_first_name + ' ' +
                        pr.participant_last_name) + ' - ' + \
                        (pr.participant_designation if
                            pr.participant_designation else '') + ', '
                    participant_html = (
                        participant_html + '<p>' +
                        (pr.participant_first_name if pr.participant_first_name
                         else '') + ' ' +
                        (pr.participant_last_name if
                         pr.participant_last_name else '') + '<br><small>' +
                        (pr.participant_designation if
                         pr.participant_designation else '') + '</small></p>')
            html_participant_list = participant_html
            show_participant_list = '<tr><td align="center"><strong>' + \
                show_participants + '</strong>' + html_participant_list + \
                '<br/></td></tr>'
            participant = participant[:-2]
        return participant, show_participant_list

    def get_rsvps(self):
        """
        Get rsvp data
        """
        show_contact_person, show_email, show_rsvp_list = '', '', ''
        contact_person, contact_email, number = '', '', ''
        rsvp_block_style = "display:none;"
        # for rsvps, display rsvps according sequence id
        if self.model.rsvps:
            show_contact_person = 'Contact Person'
            show_email = 'Contact Email'
            show_phone = 'Contact Number'
            for rsvp in sorted(
                    self.model.rsvps, key=lambda x: (x.sequence_id)):
                if rsvp.contact_person:
                    contact_person += ', ' + rsvp.contact_person
                if rsvp.email:
                    contact_email += ', ' + rsvp.email
                if rsvp.phone:
                    number += ', ' + rsvp.phone
            if contact_email != '':
                contact_email = contact_email[2:]
            if contact_person != '':
                contact_person = contact_person[2:]
                rsvp_block_style = ""
            if number != '':
                number = number[2:]
            show_rsvp_list = '<tr><td style="padding: 10px;' \
                             + rsvp_block_style + '"><table ' + \
                'width="560px" ' + \
                'bgcolor="#E6E7E8" style="padding: 10px;"><tbody><tr>' + \
                '<td colspan="3" align="center"><strong>RSVP</strong></td>' + \
                '</tr><tr><td width="110px">' + show_contact_person + \
                ':</td><td>' + contact_person + '</td></tr>' \
                '<tr><td width="110px">' + show_email + \
                ':</td><td>' + contact_email + '</td></tr>' \
                '<tr><td width="110px">'
            if number:
                show_rsvp_list += show_phone + \
                    ':</td><td>' + number + '</td>'
            show_rsvp_list += '</tr></tbody></table></td></tr>'

        return contact_person, contact_email, show_rsvp_list

    def get_dial_in_details(self):
        """
        Get dial in details data
        """
        show_dial_in_detail, show_alternative_dial_in_detail = '', ''
        dial_in_detail, alternative_dial_in_detail = '', ''
        dial_in_detail_html, alternative_dial_in_detail_html = '', ''
        if self.model.event_sub_type.show_time is True:
            show_dial_in_detail = 'Dial-in Number'
            show_alternative_dial_in_detail = 'Dial-in Number (Alt)'
            if self.model.dial_in_detail:
                dial_in_detail = self.model.dial_in_detail
            if self.model.alternative_dial_in_detail:
                alternative_dial_in_detail = \
                    self.model.alternative_dial_in_detail
            dial_in_detail_html = '<tr>' + '<td width="175px">' + \
                show_dial_in_detail + \
                '</td><td width="30px">:</td><td>' + dial_in_detail + \
                '</td></tr>'
            alternative_dial_in_detail_html = '<tr>' + '<td width="175px">' + \
                show_alternative_dial_in_detail + \
                '</td><td width="30px">:</td><td>' + \
                alternative_dial_in_detail + '</td></tr>'

        return dial_in_detail, alternative_dial_in_detail, \
            dial_in_detail_html, alternative_dial_in_detail_html

    def get_venue(self):
        """
        Get venue data
        """
        city_name, state_name, country_name, venue, venue_html, show_venue = \
            '', '', '', '', '', ''
        if self.model.city:
            city_name = self.model.city + ', '
        if self.model.state:
            state_name = self.model.state + ', '
        if self.model.country:
            country_name = self.model.country
        venue = city_name + state_name + country_name
        if city_name or country_name or state_name:
            show_venue = 'Location'
            venue_html = '<tr><td width="175px">' + show_venue + \
                '</td><td width="30px">:</td><td>' + venue + '</td></tr>'

        return venue, venue_html


class LaunchContent(BaseContentMixin):
    """
    email contents for CAE launch
    """

    def __init__(self, model):
        # setup model
        super(LaunchContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()
        self.attachment = self.get_attachment_file()
        if self.model and self.model.agendas:
            self.agendas = sorted(
                self.model.agendas, key=lambda x: (x.started_at))
        self.host, self.show_host_list = self.get_hosts()
        self.participant, self.show_participant_list = self.get_participants()
        self.contact_person, self.contact_email, self.show_rsvp_list = \
            self.get_rsvps()
        self.dial_in_detail, self.alternative_dial_in_detail, \
            self.dial_in_detail_html, self.alternative_dial_in_detail_html = \
            self.get_dial_in_details()
        self.venue, self.venue_html = self.get_venue()

    def get_invitee_content(
            self, invitee_name, cae, timezone, invitee, invitee_email):
        """
        generate invitee content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        # token generation
        payload = generate_event_book_token(invitee, APP.EVNT_CA_EVENT)
        if invitee_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                invitee_email)
        # generate event url for login or registration
        event_url = generate_event_book_email_link(
            current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'],
            cae, payload=payload)

        with open('email_html_docs/corporate_access_event/'
                  'event_launch_invitee.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('You have been invited for the event' +
                 ' - %(event_type)s of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please click on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please '

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': invitee_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'link': event_url
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': invitee_name,
            'event_type': cae.event_sub_type.name,
            'invitee_msg': 'You have been invited for the event',
            'button_label': 'Book Now',
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'link': event_url,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)
        body = body % body_dict

        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, cae, timezone, creator_email):
        """
        generate creator content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        if creator_email:
            unsubscribe_url = generate_unsubscribe_email_link(creator_email)
        with open('email_html_docs/corporate_access_event/'
                  'event_launch_creator_collaborator_participant.html',
                  'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('Your event has been created - %(event_type)s' +
                 ' of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please '

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)

        body = body % body_dict
        return subject, body, attachment, html, creator_name

    def get_host_content(self, host_name, cae, timezone, host_email):
        """
        generate host content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        if host_email:
            unsubscribe_url = generate_unsubscribe_email_link(host_email)
        with open('email_html_docs/corporate_access_event/'
                  'event_launch_host.html',
                  'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Greeting from %(brand_name)s.\r\n' + \
                'You have been designated as host by %(creator_name)s, ' + \
                'for %(event_type)s of %(company_name)s.\r\n'
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please '


        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': host_name,
            'creator_name': cae.creator.profile.first_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': host_name,
            'creator_name': cae.creator.profile.first_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)
        body = body % body_dict
        return subject, body, attachment, html, host_name

    def get_collaborator_content(self, collaborator_name, cae, timezone,
                                 collaborator_email):
        """
        generate collaborator content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        if collaborator_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                collaborator_email)
        with open('email_html_docs/corporate_access_event/'
                  'event_launch_creator_collaborator_participant.html',
                  'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('Your event has been created - %(event_type)s' +
                 ' of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please '

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': collaborator_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)
        body = body % body_dict

        return subject, body, attachment, html, collaborator_name

    def get_participant_content(self, participant_name, cae, timezone,
                                participant_email):
        """
        generate participant content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        if participant_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                participant_email)
        with open('email_html_docs/corporate_access_event/'
                  'event_launch_creator_collaborator_participant.html',
                  'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('Your event has been created - %(event_type)s' +
                 ' of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please '

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': participant_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': participant_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)
        body = body % body_dict
        return subject, body, attachment, html, participant_name

    def get_rsvp_content(self, rsvp_name, cae, timezone, rsvp_email):
        """
        generate rsvp content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        if rsvp_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                rsvp_email)
        with open('email_html_docs/corporate_access_event/'
                  'event_launch_rsvp.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('You have been invited for the event' +
                 ' - %(event_type)s of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please '

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': rsvp_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': rsvp_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**html_body_dict)
        body = body % body_dict
        return subject, body, attachment, html, rsvp_name

    def get_meeting_type_creator_content(self, creator_name, cae, timezone,
                                         creator_email):
        """
        generate content for one to one meeting creator
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        with open('email_html_docs/corporate_access_event/'
                  'event_launch_creator_collaborator_participant.html',
                  'r') as htmlfile:
            html = htmlfile.read()
        if creator_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                creator_email)
        agenda_list, agenda_body = self.get_agenda_data(timezone)

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('Your event has been created - %(event_type)s' +
                 ' of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date
            show_date_time = 'Date'

        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'alternative_dial_in_detail_html':
                self.alternative_dial_in_detail_html,
            'venue': self.venue,
            'venue_html': self.venue_html,
            'agenda_body': agenda_body,
            'unsubscribe': unsubscribe_url,
            'show_speaker_list': self.show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url}

        subject = subject % body_dict
        body = body % body_dict
        html = html.format(**body_dict)

        return subject, body, attachment, html, creator_name

    def get_meeting_type_invitee_content(
            self, invitee_name, cae, timezone, invitee, invitee_email = None):
        """
        generate invitee content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        unsubscribe_url = None
        if invitee_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                invitee_email)
        # token generation
        event_url = None
        if invitee:
            payload = generate_event_book_token(invitee, APP.EVNT_CA_EVENT)
            # generate event url for login or registration
            event_url = generate_event_book_email_link(
                current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'],
                cae, payload=payload)

        with open('email_html_docs/corporate_access_event/'
                  'event_launch_meeting.html', 'r') as htmlfile:
            html = htmlfile.read()
        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('You have been invited to the event' +
                 ' - %(event_type)s of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        body += '\r\n\n'
        body += 'Please click on the below link to login or register:\r\n\r\n'
        if invitee:
            body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'

        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.event_sub_type.show_time:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date
            show_date_time = 'Date'

        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': invitee_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'date_time': date_time,
            'venue': self.venue,
            'link': event_url,
            'unsubscribe': unsubscribe_url,
            'button_label': "Login or register",
            'logo_url': self.logo_url
        }
        subject = subject % body_dict
        body = body % body_dict
        html = html.format(**body_dict)
        return subject, body, attachment, html, invitee_name

    def get_register_invitee_content(
            self, invitee_name, cae, timezone, invitee, invitee_email):
        """
        generate invitee content
        """
        subject, body, attachment, html = '', '', self.attachment, ''
        # generate event url for login or registration
        guest_event_path = None
        if invitee.invitee_email and not invitee.user_id:
            guest_event_path = 'guest-registration?redirectTo='
        event_url = generate_event_book_email_link(
            current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'],
            cae, guest_event_path=guest_event_path)
        unsubscribe_url = None
        if invitee_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                invitee_email)

        with open('email_html_docs/corporate_access_event/'
                  'event_launch_invitee.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += ('You have been invited for the event' +
                 ' - %(event_type)s of %(company_name)s. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please click on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'user_name': invitee_name,
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'link': event_url,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            #'invitee_msg': 'You have been successfully registered for the '
            #               'event',
            'invitee_msg': 'Thank you for registering for the event',
            'button_label': 'Go To Event',
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
        }
        subject = subject % body_dict
        body = body % body_dict
        html_body_dict.update(body_dict)
        html = html.format(**html_body_dict)

        return subject, body, attachment, html, invitee_name


class EventUpdateContent(BaseContentMixin):
    """
    email contents for CAE update
    """

    def __init__(self, model):
        # setup model
        super(EventUpdateContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()
        self.attachment = self.get_attachment_file()
        if self.model and self.model.agendas:
            self.agendas = sorted(
                self.model.agendas, key=lambda x: (x.started_at))
        self.host, self.show_host_list = self.get_hosts()
        self.participant, self.show_participant_list = self.get_participants()
        self.contact_person, self.contact_email, self.show_rsvp_list = \
            self.get_rsvps()
        self.dial_in_detail, self.alternative_dial_in_detail, \
            self.dial_in_detail_html, self.alternative_dial_in_detail_html = \
            self.get_dial_in_details()
        self.venue, self.venue_html = self.get_venue()

    def get_invitee_content(self, invitee_name, cae, timezone, invitee, email):
        """
        generate invitee content
        """

        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)
        # token generation
        payload = generate_event_book_token(invitee, APP.EVNT_CA_EVENT)
        # generate event url for login or registration
        event_url = generate_event_book_email_link(
            current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'],
            cae, payload=payload)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_update_invitee.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event updates for %(company_name)s' +\
            ' %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s' +
                 ' details have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please click on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': invitee_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'link': event_url,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'link': event_url,
            'logo_url': self.logo_url
        }
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name, cae, timezone, email):
        """
        generate creator content
        """
        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event updates for %(company_name)s' +\
            ' %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s' +
                 ' details have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
        }
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, creator_name

    def get_collaborator_content(self, collaborator_name, cae, timezone,
        email):
        """
        generate collaborator content
        """
        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event updates for %(company_name)s' +\
            ' %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s' +
                 ' details have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url
        }
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, collaborator_name

    def get_host_content(self, host_name, cae, timezone, email):
        """
        generate host content
        """

        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event updates for %(company_name)s' +\
            ' %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s' +
                 ' details have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': host_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
        }
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, host_name

    def get_participant_content(self, participant_name, cae, timezone, email):
        """
        generate participant content
        """

        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event updates for %(company_name)s' +\
            ' %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s' +
                 ' details have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': participant_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
        }
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, participant_name

    def get_rsvp_content(self, rsvp_name, cae, timezone, email):
        """
        generate rsvp content
        """

        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        agenda_list, agenda_body = self.get_agenda_data(timezone)
        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event updates for %(company_name)s' +\
            ' %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s' +
                 ' details have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if self.venue:
            body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if agenda_body:
            body += 'Agendas: %(agenda_body)s'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': rsvp_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': self.venue,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'agenda_body': agenda_body,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue_html': self.venue_html,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'agenda_list': agenda_list,
            'logo_url': self.logo_url,
        }
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, rsvp_name


# #TODO: to be added after clarifying the conditions
class EventCollaboratorAddedContent(object):
    """
    email contents for CAE launch
    """

    def __init__(self, arg):
        super(EventCollaboratorAddedContent, self).__init__()
        self.arg = arg

    def get_invitee_content(self, invitee_name):
        """
        generate invitee content
        """
        subject, body, attachment, html = '', '', '', ''
        '''
        with open('email_html_docs/corporate_access_emails/'
                  'launch_invitee_email.html', 'r') as htmlfile:
                htmlfile = htmlfile.read()'''
        subject = 'NSEConnect - (company name)(event type)'
        body = 'Hi, \r\n\r\n'
        body += 'Thanks for choosing NSEConnect'
        body += '(Company Name) (Event Type) details have been updated.'
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: '
        body += 'Event Type: '
        body += 'Subject: '
        body += 'Date & Time:  '
        body += 'Venue: '
        body += 'Speaker:  '
        body += 'Contact Person: '
        body += 'Contact email: \r\n\r\n'
        body += 'Please click on the below link to login or register:'
        body += 'Login link \r\n\r\n'
        body += ('We are just a call away in case of any doubts. ' +
                 'Reach us on 022 65361001.')
        body += '\r\n\r\n Regards,'
        body += 'NSEConnect Team'
        body_dict = {'invitee_name': invitee_name}
        body = body % body_dict
        # html = htmlfile
        return subject, body, attachment, html, invitee_name

    def get_creator_content(self, creator_name):
        """
        generate creator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'NSEConnect - (company name)(event type)'
        body = 'Hi, \r\n\r\n'
        body += 'Thanks for choosing NSEConnect'
        body += '(Company Name) (Event Type) details have been updated.'
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: '
        body += 'Event Type: '
        body += 'Subject: '
        body += 'Date & Time:  '
        body += 'Venue: '
        body += 'Speaker:  '
        body += 'Contact Person: '
        body += 'Contact email: \r\n\r\n'
        body += 'Please click on the below link to login or register:'
        body += 'Login link \r\n\r\n'
        body += ('We are just a call away in case of any doubts. ' +
                 'Reach us on 022 65361001.')
        body += '\r\n\r\n Regards,'
        body += 'NSEConnect Team'
        body_dict = {'creator_name': creator_name}
        body = body % body_dict
        return subject, body, attachment, html, creator_name

    def get_collaborator_content(self, collaborator_name):
        """
        generate collaborator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'NSEConnect - (company name)(event type)'
        body = 'Hi, \r\n\r\n'
        body += 'Thanks for choosing NSEConnect'
        body += '(Company Name) (Event Type) details have been updated.'
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: '
        body += 'Event Type: '
        body += 'Subject: '
        body += 'Date & Time:  '
        body += 'Venue: '
        body += 'Speaker:  '
        body += 'Contact Person: '
        body += 'Contact email: \r\n\r\n'
        body += 'Please click on the below link to login or register:'
        body += 'Login link \r\n\r\n'
        body += ('We are just a call away in case of any doubts. ' +
                 'Reach us on 022 65361001.')
        body += '\r\n\r\n Regards,'
        body += 'NSEConnect Team'
        body_dict = {'collaborator_name': collaborator_name}
        body = body % body_dict
        return subject, body, attachment, html, collaborator_name

    # def get_host_content(self, host_name):
    #     """
    #     generate host content
    #     """
    #     subject, body, attachment, html = '', '', '', ''
    #     # #TODO: build additional content
    #     subject = 'Corporate Access Event is launched'
    #     body = 'Hi %(host_name)s, \r\n\r\n'
    #     body += 'You have been invited to host the Corporate Access Event'
    #     body += '\r\n\r\n Thanks.'
    #     body_dict = {'host_name': host_name}
    #     body = body % body_dict
    #     return subject, body, attachment, html, host_name

    def get_participant_content(self, participant_name):
        """
        generate participant content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'NSEConnect - (company name)(event type)'
        body = 'Hi, \r\n\r\n'
        body += 'Thanks for choosing NSEConnect'
        body += '(Company Name) (Event Type) details have been updated.'
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: '
        body += 'Event Type: '
        body += 'Subject: '
        body += 'Date & Time:  '
        body += 'Venue: '
        body += 'Speaker:  '
        body += 'Contact Person: '
        body += 'Contact email: \r\n\r\n'
        body += 'Please click on the below link to login or register:'
        body += 'Login link \r\n\r\n'
        body += ('We are just a call away in case of any doubts. ' +
                 'Reach us on 022 65361001.')
        body += '\r\n\r\n Regards,'
        body += 'NSEConnect Team'
        body_dict = {'participant_name': participant_name}
        body = body % body_dict
        return subject, body, attachment, html, participant_name

    def get_rsvp_content(self, rsvp_name):
        """
        generate rsvp content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'NSEConnect - (company name)(event type)'
        body = 'Hi, \r\n\r\n'
        body += 'Thanks for choosing NSEConnect'
        body += '(Company Name) (Event Type) details have been updated.'
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: '
        body += 'Event Type: '
        body += 'Subject: '
        body += 'Date & Time:  '
        body += 'Venue: '
        body += 'Speaker:  '
        body += 'Contact Person: '
        body += 'Contact email: \r\n\r\n'
        body += 'Please click on the below link to login or register:'
        body += 'Login link \r\n\r\n'
        body += ('We are just a call away in case of any doubts. ' +
                 'Reach us on 022 65361001.')
        body += '\r\n\r\n Regards,'
        body += 'NSEConnect Team'
        body_dict = {'rsvp_name': rsvp_name}
        body = body % body_dict
        return subject, body, attachment, html, rsvp_name


class EventCompletionContent(BaseContentMixin):
    """
    email contents for CAE completion
    """

    def __init__(self, model):
        # setup model
        super(EventCompletionContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()

    def get_attendee_content(self, attendee_name, cae, attendee_email):
        """
        generate attendee content
        """
        unsubscribe_url = None
        if attendee_email:
            unsubscribe_url = generate_unsubscribe_email_link(attendee_email)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_completion.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Thank you for attending %(event_type)s'
        body = 'Hi %(user_name)s, \r\n'
        body += ('%(company_name)s would like to thank you for attending ' +
                 'our %(event_type)s. Hope you enjoyed the experience and' +
                 ' we look forward to see you at the next event. \r\n\r\n')
        body += 'We truly appreciate your support. ' + \
                'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        body_dict = {
            'user_name': attendee_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body.format(**body_dict)
        return subject, body, attachment, html, attendee_name

    def get_participant_content(self, participant_name, cae, email):
        """
        generate participant content
        """

        unsubscribe_url = None
        if email:
            unsubscribe_url = generate_unsubscribe_email_link(email)

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_completion.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Thank you for attending %(event_type)s'
        body = 'Hi %(user_name)s, \r\n'
        body += ('%(company_name)s would like to thank you for attending ' +
                 'our %(event_type)s. Hope you enjoyed the experience and' +
                 ' we look forward to see you at the next event. \r\n\r\n')
        body += 'We truly appreciate your support. ' + \
                'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        body_dict = {
            'user_name': participant_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        subject = subject % body_dict
        html = html.format(**body_dict)
        body = body.format(**body_dict)
        return subject, body, attachment, html, participant_name


# #TODO: Merged with slot update content, maybe to
class SlotTimeChangeContent(object):
    """
    email contents for CAE slot time change
    """

    def __init__(self, arg):
        super(SlotTimeChangeContent, self).__init__()
        self.arg = arg

    def get_collaborator_content(self, collaborator_name):
        """
        generate collaborator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'Corporate Access Event Slot time is changed'
        body = 'Hi %(collaborator_name)s, \r\n\r\n'
        body += ('The Corporate Access Event you are collaborating' +
                 ' has a change in its time slot')
        body += '\r\n\r\n Thanks.'
        body_dict = {'collaborator_name': collaborator_name}
        body = body % body_dict
        return subject, body, attachment, html, collaborator_name

    def get_slot_inquirer_content(self, inquirer_name):
        """
        generate collaborator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'Corporate Access Event Slot time is changed'
        body = 'Hi %(inquirer_name)s, \r\n\r\n'
        body += ('The Corporate Access Event Slot you inquired about' +
                 ' has changed its timing')
        body += '\r\n\r\n Thanks.'
        body_dict = {'inquirer_name': inquirer_name}
        body = body % body_dict
        return subject, body, attachment, html, inquirer_name

    def get_creator_content(self, creator_name):
        """
        generate creator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'Corporate Access Event Slot time is changed'
        body = 'Hi %(creator_name)s, \r\n\r\n'
        body += ('The Corporate Access Event you created' +
                 ' has a change in its time slot')
        body += '\r\n\r\n Thanks.'
        body_dict = {'creator_name': creator_name}
        body = body % body_dict
        return subject, body, attachment, html, creator_name


class SlotUpdatedContent(BaseContentMixin):
    """
    email contents for CAE slot updated
    """

    def __init__(self, model):
        # setup model
        super(SlotUpdatedContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()
        self.host, self.show_host_list = self.get_hosts()
        self.participant, self.show_participant_list = self.get_participants()
        self.contact_person, self.contact_email, self.show_rsvp_list = \
            self.get_rsvps()
        self.dial_in_detail, self.alternative_dial_in_detail, \
            self.dial_in_detail_html, self.alternative_dial_in_detail_html = \
            self.get_dial_in_details()

    def get_collaborator_content(self, collaborator_name, cae,
                                 cae_slot, timezone, email):
        """
        generate collaborator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = ('%(brand_name)s - Event updates for ' +
                   '%(company_name)s %(event_type)s')
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s details' +
                 ' have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, collaborator_name

    def get_slot_inquirer_content(self, inquirer_name, cae,
                                  cae_slot, timezone, email):
        """
        generate collaborator content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = ('%(brand_name)s - Event updates for ' +
                   '%(company_name)s %(event_type)s')
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s details' +
                 ' have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': inquirer_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': inquirer_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe':unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, inquirer_name

    def get_creator_content(self, creator_name, cae, cae_slot, timezone,
        email):
        """
        generate creator content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_update.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = ('%(brand_name)s - Event updates for ' +
                   '%(company_name)s %(event_type)s')
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('%(company_name)s %(event_type)s details' +
                 ' have been updated. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, creator_name


# #TODO: to be deleted, need confirmation
class SlotDeletedContent(object):
    """
    email contents for CAE slot Deleted
    """

    def __init__(self, arg):
        super(SlotDeletedContent, self).__init__()
        self.arg = arg

    def get_collaborator_content(self, collaborator_name):
        """
        generate collaborator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'Corporate Access Event Slot is Deleted'
        body = 'Hi %(collaborator_name)s, \r\n\r\n'
        body += ('The Corporate Access Event you are collaborating' +
                 ' has a slot Deleted')
        body += '\r\n\r\n Thanks.'
        body_dict = {'collaborator_name': collaborator_name}
        body = body % body_dict
        return subject, body, attachment, html, collaborator_name

    def get_slot_inquirer_content(self, inquirer_name):
        """
        generate collaborator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'Corporate Access Event Slot is Deleted'
        body = 'Hi %(inquirer_name)s, \r\n\r\n'
        body += ('The Corporate Access Event Slot you inquired about' +
                 ' is slot Deleted')
        body += '\r\n\r\n Thanks.'
        body_dict = {'inquirer_name': inquirer_name}
        body = body % body_dict
        return subject, body, attachment, html, inquirer_name

    def get_creator_content(self, creator_name):
        """
        generate creator content
        """
        subject, body, attachment, html = '', '', '', ''
        # #TODO: build additional content
        subject = 'Corporate Access Event Slot is Deleted'
        body = 'Hi %(creator_name)s, \r\n\r\n'
        body += ('The Corporate Access Event you created' +
                 ' has a slot Deleted')
        body += '\r\n\r\n Thanks.'
        body_dict = {'creator_name': creator_name}
        body = body % body_dict
        return subject, body, attachment, html, creator_name


class SlotInquiryGenerationContent(BaseContentMixin):
    """
    email contents for CAE slot inquiry generation
    """

    def __init__(self, model):
        # setup model
        super(SlotInquiryGenerationContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()
        self.host, self.show_host_list = self.get_hosts()
        self.participant, self.show_participant_list = self.get_participants()
        self.contact_person, self.contact_email, self.show_rsvp_list = \
            self.get_rsvps()
        self.dial_in_detail, self.alternative_dial_in_detail, \
            self.dial_in_detail_html, self.alternative_dial_in_detail_html = \
            self.get_dial_in_details()

    def get_collaborator_content(self, collaborator_name, cae,
                                 cae_slot, timezone, email):
        """
        generate collaborator content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_generation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = ('%(brand_name)s - Event inquiry for ' +
                   '%(company_name)s %(event_type)s')
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s has ' +
                 'been generated. You will receive a confirmation email once' +
                 ' the creator confirms your request. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Inquired for Slot Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Inquired for Slot Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, collaborator_name

    def get_slot_inquirer_content(self, inquirer_name, cae,
                                  cae_slot, timezone, email):
        """
        generate inquirer content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_generation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = ('%(brand_name)s - Event inquiry for ' +
                   '%(company_name)s %(event_type)s')
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s has ' +
                 'been generated. You will receive a confirmation email once' +
                 ' the creator confirms your request. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Inquired for Slot Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Inquired for Slot Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': inquirer_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': inquirer_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, inquirer_name

    def get_creator_content(self, creator_name, cae, cae_slot, timezone,
        email):
        """
        generate creator content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_generation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = ('%(brand_name)s - Event inquiry for ' +
                   '%(company_name)s %(event_type)s')
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s has ' +
                 'been generated. You will receive a confirmation email once' +
                 ' the creator confirms your request. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Inquired for Slot Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Inquired for Slot Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, creator_name


class SlotInquiryConfirmationContent(BaseContentMixin):
    """
    email contents for CAE slot inquiry confirmation
    """

    def __init__(self, model):
        # setup model
        super(SlotInquiryConfirmationContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()
        self.host, self.show_host_list = self.get_hosts()
        self.participant, self.show_participant_list = self.get_participants()
        self.contact_person, self.contact_email, self.show_rsvp_list = \
            self.get_rsvps()
        self.dial_in_detail, self.alternative_dial_in_detail, \
            self.dial_in_detail_html, self.alternative_dial_in_detail_html = \
            self.get_dial_in_details()

    def get_collaborator_content(self, collaborator_name, cae,
                                 cae_slot, timezone):
        """
        generate collaborator content
        """

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_confirmation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event confirmation for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been confirmed. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time: (Confirmed) '
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date: (Confirmed) '
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
            'show_speaker_list': host,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': collaborator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, collaborator_name

    def get_slot_inquirer_content(self, inquirer_name, cae,
                                  cae_slot, timezone, email):
        """
        generate inquirer content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_confirmation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event confirmation for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been confirmed. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time: (Confirmed) '
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date: (Confirmed) '
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': inquirer_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': inquirer_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url,
            'unsubscribe' : unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, inquirer_name

    def get_creator_content(self, creator_name, cae, cae_slot, timezone):
        """
        generate creator content
        """

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_confirmation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event confirmation for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been confirmed. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time: (Confirmed) '
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date: (Confirmed) '
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, creator_name

    def get_participant_content(self, participant_name, cae,
                                cae_slot, timezone):
        """
        generate participant content
        """

        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_confirmation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = '%(brand_name)s - Event confirmation for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been confirmed. \r\n')
        body += 'Please find the event details below: \r\n\r\n'
        body += 'Company Name: %(company_name)s\r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s %(date_time)s\r\n'
        body += 'Venue: %(venue)s\r\n'
        if self.model.event_sub_type.show_time is True:
            body += 'Dial-in Number: %(dial_in_detail)s\r\n'
            body += 'Dial-in Number (Alt): ' + \
                    '%(alternative_dial_in_detail)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        if self.participant:
            body += 'Participants: %(participant_list)s\r\n'
        if self.contact_person:
            body += 'Contact Person: %(contact_person)s\r\n'
        if self.contact_email:
            body += 'Contact Email: %(contact_email)s\r\n'
        body += '\r\n\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        start_date, start_time, end_date, address = '', '', '', ''
        if cae_slot.started_at:
            start_date_obj = time_converter(cae_slot.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae_slot.ended_at:
            end_date_obj = time_converter(cae_slot.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae_slot.address:
            address = cae_slot.address
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Slot Date & Time: (Confirmed) '
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Slot Date: (Confirmed) '
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': participant_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'event_type': cae.event_sub_type.name,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail': self.dial_in_detail,
            'alternative_dial_in_detail': self.alternative_dial_in_detail,
            'venue': address,
            'show_speaker_list': host,
            'contact_person': self.contact_person,
            'contact_email': self.contact_email,
            'participant_list': self.participant,
        }
        html_body_dict = {
            'show_date_time': show_date_time,
            'user_name': participant_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'dial_in_detail_html': self.dial_in_detail_html,
            'alternative_dial_in_detail_html':
            self.alternative_dial_in_detail_html,
            'venue': address,
            'show_speaker_list': show_host_list,
            'show_rsvp_list': self.show_rsvp_list,
            'show_participant_list': self.show_participant_list,
            'logo_url': self.logo_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, participant_name


class SlotInquiryDeletionContent(BaseContentMixin):
    """
    email contents for CAE slot inquiry deletion
    """

    def __init__(self, model):
        # setup model
        super(SlotInquiryDeletionContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()

    def get_collaborator_content(self, collaborator_name, cae, email):
        """
        generate collaborator content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_cancellation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Event request cancelled for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been cancelled. \r\n')
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': collaborator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
        }
        html_body_dict = {
            'user_name': collaborator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, collaborator_name

    def get_slot_inquirer_content(self, inquirer_name, cae, email):
        """
        generate collaborator content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_cancellation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Event request cancelled for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been cancelled. \r\n')
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': inquirer_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
        }
        html_body_dict = {
            'user_name': inquirer_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, inquirer_name

    def get_creator_content(self, creator_name, cae, email):
        """
        generate creator content
        """
        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_cancellation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Event request cancelled for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been cancelled. \r\n')
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': creator_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
        }
        html_body_dict = {
            'user_name': creator_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, creator_name

    def get_participant_content(self, participant_name, cae, email):
        """
        generate participant content
        """

        unsubscribe_url = generate_unsubscribe_email_link(email)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'slot_inquiry_cancellation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile
        subject = '%(brand_name)s - Event request cancelled for ' +\
            '%(company_name)s %(event_type)s'
        subject_dict = {
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
            'brand_name': current_app.config['BRAND_NAME']
        }
        subject = subject % subject_dict
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'Thanks for choosing %(brand_name)s \r\n'
        body += ('Your inquiry for %(company_name)s %(event_type)s' +
                 ' has been cancelled. \r\n')
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body_dict = {
            'user_name': participant_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'event_type': cae.event_sub_type.name,
        }
        html_body_dict = {
            'user_name': participant_name,
            'event_type': cae.event_sub_type.name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'brand_name': current_app.config['BRAND_NAME'],
            'company_name': cae.account.account_name,
            'logo_url': self.logo_url,
            'unsubscribe': unsubscribe_url
        }
        body = body % body_dict
        html = html.format(**html_body_dict)
        return subject, body, attachment, html, participant_name


class CancellationContent(BaseContentMixin):
    """
    email contents for CAE cancellation
    """

    def __init__(self, model):
        # setup model
        super(CancellationContent, self).__init__(model)
        # setup other attributes
        self.logo_url = self.get_logo_url()
        self.host, self.show_host_list = self.get_hosts()

    def get_invitee_content(self, invitee_name, cae, timezone, invitee,
                            invitee_email=None):
        """
        generate invitee content
        """
        unsubscribe_url = None
        if invitee_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                invitee_email)
        # token generation
        payload = generate_event_book_token(invitee, APP.EVNT_CA_EVENT)
        # generate event url for login or registration
        event_url = generate_event_book_email_link(
            current_app.config['CORPACCS_EVENT_JOIN_ADD_URL'],
            cae, payload=payload)
        subject, body, attachment, html = '', '', '', ''
        with open('email_html_docs/corporate_access_event/'
                  'event_cancellation.html', 'r') as htmlfile:
            htmlfile = htmlfile.read()
        html = htmlfile

        host, show_host_list = self.host, self.show_host_list

        subject = 'Event cancelled - %(event_name)s of %(company_name)s'
        body = 'Hi %(user_name)s, \r\n\r\n'
        body += 'We regret to inform that the ' + \
                '%(event_name)s of %(company_name)s has been cancelled. ' + \
                'Thank You for showing interest in the event.\r\n\r\n'
        body += 'Event Details \r\n\r\n'
        body += 'Status: Cancelled \r\n'
        body += 'Event Type: %(event_type)s\r\n'
        body += '%(show_date_time)s: %(date_time)s\r\n'
        if cae.corporate_access_event_hosts:
            body += 'Speaker: %(show_speaker_list)s\r\n'
        body += '\r\n\n'
        body += 'To find details of the upcoming events please click' + \
                ' on the below link to login or register:\r\n\r\n'
        body += '%(link)s \r\n\r\n\r\n'
        body += 'Please let us know if you have any queries by emailing ' + \
                'us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
        body += '\r\n\n'
        body += 'If you don\'t want to receive this type of email ' \
                'in the future, please %(unsubscribe)s'
        start_date, start_time, end_date = '', '', ''
        if cae.started_at:
            start_date_obj = time_converter(cae.started_at, to=timezone)
            start_date = dt.strftime(start_date_obj, '%d %B %Y')
            start_time = dt.strftime(start_date_obj, '%I:%M %p')
        if cae.ended_at:
            end_date_obj = time_converter(cae.ended_at, to=timezone)
            end_date = dt.strftime(end_date_obj, '%d %B %Y')
        if cae.event_sub_type.show_time is True:
            date_time = start_date + ' ' + start_time
            show_date_time = 'Date & Time'
        else:
            date_time = start_date + ' To ' + end_date
            show_date_time = 'Date'
        body_dict = {
            'show_date_time': show_date_time,
            'user_name': invitee_name,
            'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'event_type': cae.event_sub_type.name,
            'event_name': cae.title,
            'company_name': cae.account.account_name,
            'date_time': date_time,
            'show_speaker_list': host,
            'link': event_url,
            'unsubscribe': unsubscribe_url
        }
        html_body_dict = {
            'show_speaker_list': show_host_list,
            'logo_url': self.logo_url,
        }
        subject = subject % body_dict
        body = body % body_dict
        html_body_dict = body_dict.update(html_body_dict)
        html = html.format(**html_body_dict)

        return subject, body, attachment, html, invitee_name
