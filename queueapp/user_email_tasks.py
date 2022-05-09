"""
User email related tasks, for each type of email
"""

from flask import current_app, render_template
from datetime import datetime as dt

from app import db
from app.common.utils import time_converter
from app.resources.registration_requests.models import RegistrationRequest
from app.resources.registration_requests.helpers import \
    generate_verify_email_link
from app.resources.users.models import User
from app.base import constants as APP

from queueapp.tasks import celery_app, logger, send_email_actual


@celery_app.task(bind=True, ignore_result=True)
def send_verify_email_email(self, result, row_id, *args, **kwargs):
    """
    Sends the verify email + registration, email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the registration request
    """

    if result:
        try:
            # first find the registration request
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                return False

            # generate the link
            link = generate_verify_email_link(model)

            # generate the email content
            to_addresses = [model.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            bcc_addresses = current_app.config[
                'DEFAULT_REG_REQ_CONTACT_EMAILS']
            reply_to = ''
            subject = ' Welcome to {} Community'.format(
                current_app.config['BRAND_NAME'])
            attachment = ''
            template_file = 'verify_email.html'

            body = 'Welcome {user_name},\r\n\r\n' + \
                'Welcome to {brand_name} and Thank You for signing up.' +\
                '\r\n\r\nAbout {brand_name}\r\n\r\n' + \
                'Exchange Connect is a platform for digitizing ' + \
                'capital market workflow for companies. It is a suite of ' + \
                'modules that simplify the process of investor engagement.' + \
                ' Our technology provides insightful data and actionable ' +\
                'suggestions relevant to each user.' + \
                '\r\n\r\nPlease click on the below link to login:' +\
                '\r\n {link} \r\n\r\n' +\
                'Please let us know if you have any queries by ' + \
                'emailing us on {helpdesk_email} or call us on ' + \
                '{helpdesk_number}.\r\n\r\nThank You,\r\n' + \
                '{sign_off_name}'
            if model.only_design_lab:
                body = "Hello {user_name},\r\n\r\n" \
                       "Welcome to Design Lab where you get websites and " \
                       "presentations done in a seamless and transparent " \
                       "manner and quick time. Please click this {link}" \
                       " to complete your verification and start creating" \
                       " projects."
                template_file = 'designlab_verify_email.html'
                subject = 'Team Design Lab'

            body_dict = {
                'user_name': model.first_name,
                'link': link,
                'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
                'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
                'brand_name': current_app.config['BRAND_NAME'],
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}

            body = body.format(**body_dict)
            html = render_template(
                'registration_requests/' + template_file, **body_dict)
            # send user email
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.USER_ACTIVITY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    bcc_addresses = bcc_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)
                # User.query.filter_by(email=model.email).update(
                #     {'is_mail_sent': True}, synchronize_session=False)

                User.query.filter_by(email=model.email).update(
                    {'verify_mail_sent': True}, synchronize_session=False)
                db.session.commit()
            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_user_welcome_email(self, result, row_id, *args, **kwargs):
    """
    Sends the verify email + registration, email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the registration request
    """

    if result:
        try:
            # first find the registration request
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                return False

            # generate the email content
            to_addresses = [model.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = ' Welcome to {brand_name} Community'
            html = ''
            body = 'Dear {user_name},\r\n\r\n' + \
                   'Greetings from  {brand_name}.' + \
                   '\r\n\r\n' + \
                   'We have received your registration request and ' \
                   'welcome you to {brand_name} Community.\n' + \
                   'You will shortly receive a verification email, ' \
                   'kindly click on the link to verify and login.\r\n\n' + \
                   'About {brand_name} A platform for digitizing capital ' \
                   'market interface for companies and suite of modules that ' \
                   'simplify the process of investor engagement.' + \
                   '\r\n\r\n'
            body += 'Please let us know if you have any queries by ' + \
                    'emailing us on {helpdesk_email} or call us on ' + \
                    '{helpdesk_number}.\r\n\r\nThank You,\r\n' + \
                    '{sign_off_name}'
            body_dict = {
                'user_name': model.first_name,
                'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
                'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
                'brand_name': current_app.config['BRAND_NAME'],
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
            design_lab_subject = "welcome to design lab"
            design_lab_body = "hello {user_name}\r\n\r\n" \
                              "Thank you for registering in Design Lab.\n" \
                              "Now save time and effort by assigning website " \
                              "and presentation projects within minutes " \
                              "using our plug-in.\r\n\r\n" \
                              "For queries, contact {helpdesk_email} and " \
                              "{helpdesk_number}."

            body_dict['iframe_url'] = current_app.config['DESIGN_LAB_IFRAME_URL']
            html_template = 'user_welcome_email.html'
            if model.only_design_lab:
                html_template = 'designlab_user_welcome_email.html'
                body, subject = design_lab_body, design_lab_subject
            html = render_template('registration_requests/'
                      + html_template, **body_dict)
            attachment = ''
            subject = subject.format( **body_dict)
            body = body.format(**body_dict)
            # send user email
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.USER_ACTIVITY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)

                model.welcome_mail_sent = True
                db.session.add(model)
                db.session.commit()

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_invitation_verify_email_email(self, result, row_id, *args, **kwargs):
    """
    Sends the verify email + registration, email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the registration request
    """

    if result:
        try:
            # first find the registration request
            html = ''
            model = RegistrationRequest.query.get(row_id)
            if int(model.domain_id) == 8:
                with open('email_html_docs/uae_user_invitation_email_'
                      'template.html', 'r') as htmlfile:
                    html = htmlfile.read()
            else:
                with open('email_html_docs/user_invitation_email_'
                          'template.html', 'r') as htmlfile:
                    html = htmlfile.read()
            if model is None or model.deleted:
                return False

            # generate the link
            link = generate_verify_email_link(model)

            # generate the email content
            to_addresses = [model.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            bcc_addresses = current_app.config[
                'DEFAULT_REG_REQ_CONTACT_EMAILS']
            reply_to = ''
            subject = ' Invitation to %(brand_name)s Platform'
            attachment = ''
            subject = subject % {
                'brand_name': current_app.config['BRAND_NAME']}
            body = "Dear %(user_name)s,\r\n\r\n" + \
                "We invite you to our online platform %(brand_name)s. The " +\
                "platform is designed to break the communication barriers " +\
                "and provide a dynamic digital ecosystem for Companies, " +\
                "Buy-Side, Sell-Side and Family Offices/Investors\r\n" +\
                "\r\n\r\nPlease click on the below link to login:" +\
                "\r\n" + link + "\r\n\r\n"
            body += 'Please let us know if you have any queries by ' + \
                'emailing us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'

            body_dict = {
                'user_name': model.first_name,
                'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
                'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
                'brand_name': current_app.config['BRAND_NAME'],
                'link': link,
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}

            body = body % body_dict
            html = html.format(**body_dict)
            # send user email
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.USER_ACTIVITY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    bcc_addresses=bcc_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)
                User.query.filter_by(email=model.email).update(
                    {'verify_mail_sent': True}, synchronize_session=False)
                db.session.commit()

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_password_change_email(self, result, row_id, *args, **kwargs):
    """
    Sends the password change successful email to the user

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the user
    """

    if result:
        try:
            user = User.query.get(row_id)
            if user is None or user.deleted:
                return False
            # generate the email content
            to_addresses = [user.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = '%(brand_name)s Community Password Change'
            html = ''
            with open('email_html_docs/'
                      'password_reset_notify_template.html', 'r') as htmlfile:
                html = htmlfile.read()
            attachment = ''
            subject = subject % {
                'brand_name': current_app.config['BRAND_NAME']}
            body = 'Greetings %(user_name)s,\r\n\r\n' + \
                'We just wanted to let you know that our records ' + \
                'show that you changed your password with us recently.' + \
                '\r\n\r\n'
            body += 'Please let us know if you have any queries by ' + \
                'emailing us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
            body_dict = {
                'user_name': user.profile.first_name,
                'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
                'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
            body = body % body_dict
            html = html.format(**body_dict)
            # send user email
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.USER_ACTIVITY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def designlab_send_password_change_email(self, result, row_id, *args, **kwargs):
    """
    Sends the password change successful email to the user

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the user
    """

    if result:
        try:
            user = User.query.get(row_id)
            if user is None or user.deleted:
                return False
            # generate the email content
            to_addresses = [user.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = 'Team Design Lab'
            html = ''
            with open('email_html_docs/'
                      'designlab_password_reset_notify_template.html', 'r') as htmlfile:
                html = htmlfile.read()
            attachment = ''
            body = 'Greetings %(user_name)s,\r\n\r\n' + \
                'We just wanted to let you know that our records ' + \
                'show that you changed your password with us recently.' + \
                '\r\n\r\n'
            body += 'Please let us know if you have any queries by ' + \
                'emailing us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nWarm regards,\r\n' + \
                'Team Design Lab'
            body_dict = {
                'user_name': user.profile.first_name,
                'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
                'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
            body = body % body_dict
            html = html.format(**body_dict)
            # send user email
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.USER_ACTIVITY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_registration_request_email(self, result, row_id, *args, **kwargs):
    """
    Sends the registration_request email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the registration request
    """

    if result:
        try:
            # first find the registration request
            model = RegistrationRequest.query.get(row_id)
            if model is None or model.deleted:
                return False

            # generate the email content
            to_addresses = current_app.config['DEFAULT_REG_REQ_CONTACT_EMAILS']
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = 'Request Received from %(user_name)s'
            subject = subject % {
                'user_name': model.first_name + ' ' + model.last_name}
            html = ''
            # with open('email_html_docs/registration_requests/'
            #           'registration_request_received_email.html', 'r') \
            #         as htmlfile:
            #     html = htmlfile.read()
            attachment = ''
            body = 'Hi Team, \r\n\r\n'
            body += 'We have received a registration request. Please' + \
                    ' find the details below: \r\n\r\n'
            body += 'Domain: {domain}\r\n'
            body += 'Date: {date}\r\n'
            body += 'Time: {time}\r\n\r\n'
            body += 'Name: {user_name}\r\n'
            body += 'Type: {account_type}\r\n'
            body += 'Company: {company_name}\r\n'
            body += 'Email: {email}\r\n'
            body += 'Tel.: {phone_number}\r\n\r\n'
            body += 'Regards,\r\n' + \
                    '{sign_off_name}'
            date_time_obj = time_converter(model.created_date)
            date = dt.strftime(date_time_obj, '%d %B %Y')
            time = dt.strftime(date_time_obj, '%I:%M %p')
            domain_name = model.domain.country if model.domain else ""
            body_dict = {
                'date': date,
                'time': time,
                'user_name': model.first_name + ' ' + model.last_name,
                'first_name': model.first_name,
                'last_name': model.last_name,
                'account_type': model.join_as,
                'email': model.email,
                'company_name': model.company if model.company else '',
                'phone_number':
                    model.phone_number if model.phone_number else '',
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
                'domain': domain_name}
            body = body.format(**body_dict)
            template = 'registration_request_received_email.html'
            if model.only_design_lab:
                template = 'designlab_reg_request_received.html'
            html = render_template('registration_requests/'+template,
                                   **body_dict)
            # send email to concerned people
            if not current_app.config['DEBUG']:
                send_email_actual(
                    subject=subject, from_name=from_name,
                    keywords=APP.USER_ACTIVITY_EMAIL,
                    from_email=from_email, to_addresses=to_addresses,
                    reply_to=reply_to, body=body, html=html,
                    attachment=attachment)

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result
