"""
personalised video invitee email body type related helper
"""

import os
import requests

from datetime import datetime as dt
from flask import current_app, render_template
from app.common.utils import time_converter
from app.base import constants as APP
from app.common.helpers import generate_event_book_token, \
    generate_event_book_email_link, generate_video_email_link

from app.common.helpers import generate_video_token, \
    verify_video_token
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

    # def get_logo_url(self):
    #     """
    #     Get the logo url from the event if not,
    #     get it from event account if not, get default one.
    #     """
    #     logo_url = self.model.invite_logo_url
    #     if not logo_url:
    #         self.model.load_urls()
    #         logo_url = self.model.invite_logo_url
    #         if not logo_url:
    #             logo_url = self.model.account.profile.profile_photo_url
    #             if not logo_url:
    #                 self.model.account.profile.load_urls()
    #                 logo_url = self.model.account.profile.profile_photo_url
    #                 if not logo_url:
    #                     logo_url = current_app.config[
    #                         'DEFAULT_CA_EVENT_LOGO_URL']
    #
    #     return logo_url
    #
    # def get_attachment_file(self):
    #     """
    #     Get filename from CAEvent attachment
    #     """
    #     attachment = ''
    #     if self.model.attachment:
    #         self.model.load_urls()
    #         attachment_url = self.model.attachment_url
    #         response = requests.get(attachment_url)
    #         file = os.path.join(
    #             current_app.config['BASE_DOWNLOADS_FOLDER'],
    #             self.model.attachment)
    #         with open(file, 'wb') as f:
    #             f.write(response.content)
    #             attachment = file
    #     return attachment


class LaunchContent(BaseContentMixin):
    """
    email contents for CAE launch
    """

    def __init__(self, model):
        # setup model
        super(LaunchContent, self).__init__(model)
        # setup other attributes
        # self.logo_url = self.get_logo_url()
        # self.attachment = self.get_attachment_file()
        #still left to do
        # self.contact_person, self.contact_email = self.write_some_code_to_get_this()

    def get_invitee_content(
            self, invitee_name, pr, invitee, invitee_email):
        """
        generate invitee content
        """
        subject, body, html = '', '', ''
        unsubscribe_url = None
        # token generation
        payload = generate_video_token(invitee, APP.VID_TEASER)
        if invitee_email:
            unsubscribe_url = generate_unsubscribe_email_link(
                invitee_email)
        # generate event url for login or registration
        # event_url = generate_event_book_email_link(
        #     current_app.config['PERSONALISED_VIDEO_URL'],
        #     cae, payload=payload)
        #generate personalised video url
        video_url = generate_video_email_link(current_app.config['PERSONALISED_VIDEO_JOIN_ADD_URL'],
                                              pr.video_type, payload=payload) #generate video url calling function here
        # with open('email_html_docs/personalised_video/sample_pv_invitee.html', 'r') as htmlfile:
        #     htmlfile = htmlfile.read()
        # html = htmlfile
        # agenda_list, agenda_body = self.get_agenda_data(timezone)
        # host, show_host_list = self.host, self.show_host_list

        # subject = 'Watch Now: Your personalised video demo of ExchangeConnect is ready!'
        #
        #
        # # subject = '%(brand_name)s - %(company_name)s %(event_type)s'
        # body = 'Hi %(user_name)s, \r\n\r\n'
        # body += 'Do you agree that the financial industry needs to adopt technology just like every other industry is?'
        # body +=  ('You have been invited for the event' +
        #         ' - %(event_type)s of %(company_name)s. \r\n')
        # body += 'Please find the event details below: \r\n\r\n'
        # body += 'Company Name: %(company_name)s\r\n'
        # body += 'Event Type: %(event_type)s\r\n'
        # body += '%(show_date_time)s: %(date_time)s\r\n'
        # if self.venue:
        #     body += 'Venue: %(venue)s\r\n'
        # if self.model.event_sub_type.show_time is True:
        #     body += 'Dial-in Number: %(dial_in_detail)s\r\n'
        #     body += 'Dial-in Number (Alt): ' + \
        #             '%(alternative_dial_in_detail)s\r\n'
        # if cae.corporate_access_event_hosts:
        #     body += 'Speaker: %(show_speaker_list)s\r\n'
        # if self.participant:
        #     body += 'Participants: %(participant_list)s\r\n'
        # if agenda_body:
        #     body += 'Agendas: %(agenda_body)s'
        # if self.contact_person:
        #     body += 'Contact Person: %(contact_person)s\r\n'
        # if self.contact_email:
        #     body += 'Contact Email: %(contact_email)s\r\n'
        # body += '\r\n\n'
        # body += 'Please click on the below link to login or register:\r\n\r\n'
        # body += '%(link)s \r\n\r\n\r\n'
        # body += 'Please let us know if you have any queries by emailing ' + \
        #         'us on %(helpdesk_email)s or call us on ' + \
        #         '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
        #         '%(sign_off_name)s'
        # body += '\r\n\n'
        # body += 'If you don\'t want to receive this type of email ' \
        #         'in the future, please '
        #
        # start_date, start_time, end_date = '', '', ''
        # if cae.started_at:
        #     start_date_obj = time_converter(cae.started_at, to=timezone)
        #     start_date = dt.strftime(start_date_obj, '%d %B %Y')
        #     start_time = dt.strftime(start_date_obj, '%I:%M %p')
        # if cae.ended_at:
        #     end_date_obj = time_converter(cae.ended_at, to=timezone)
        #     end_date = dt.strftime(end_date_obj, '%d %B %Y')
        # if cae.event_sub_type.show_time is True:
        #     date_time = start_date + ' ' + start_time
        #     show_date_time = 'Date & Time'
        # else:
        #     date_time = start_date + ' To ' + end_date
        #     show_date_time = 'Date'
        # body_dict = {
        #     'show_date_time': show_date_time,
        #     'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
        #     'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
        #     'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
        #     'company_name': current_app.config['BRAND_NAME'],
        #     'user_name': invitee_name,
        #     'contact_person': self.contact_person,
        #     'contact_email': self.contact_email,
        #     'link': video_url
        # }
        # html_body_dict = {
        #     'show_date_time': show_date_time,
        #     'user_name': invitee_name,
        #     'event_type': cae.event_sub_type.name,
        #     'invitee_msg': 'You have been invited for the event',
        #     'button_label': 'Book Now',
        #     'helpdesk_number': current_app.config['CA_HELPDESK_NUMBER'],
        #     'helpdesk_email': current_app.config['CA_HELPDESK_EMAIL'],
        #     'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
        #     'company_name': cae.account.account_name,
        #     'date_time': date_time,
        #     'dial_in_detail_html': self.dial_in_detail_html,
        #     'alternative_dial_in_detail_html':
        #     self.alternative_dial_in_detail_html,
        #     'venue_html': self.venue_html,
        #     'show_speaker_list': show_host_list,
        #     'show_rsvp_list': self.show_rsvp_list,
        #     'show_participant_list': self.show_participant_list,
        #     'agenda_list': agenda_list,
        #     'link': event_url,
        #     'logo_url': self.logo_url,
        #     'unsubscribe': unsubscribe_url
        # }
        # subject = subject % body_dict
        # html = html.format(**html_body_dict)
        # body = body % body_dict

        subject = 'Watch Now: Your personalised video demo of ExchangeConnect is ready!'

        html_body_dict = {
            'user_name':'kajal',
            'company_name':'wirpo',
            'link':video_url
        }
        body_dict = {
            'user_name': 'kajal',
            'company_name': 'wirpo',
            'link': video_url
        }

        # html = render_template(
        #     'personalised_video/sample_invitee.html', **html_body_dict)
        subject = subject
        html = render_template(
            'personalised_video/sample_invitee.html')
        body = body % body_dict

        return subject, body, html, invitee_name

