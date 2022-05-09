"""
Personalised video email related tasks. for each type
"""
from flask import current_app, render_template
from datetime import datetime as dt
from datetime import date

from app import db
from app.common.utils import time_converter
from app.base import constants as APP
from app.common.helpers import generate_video_token, generate_video_email_link
from app.resources.personalised_video.models import PersonalisedVideoMaster
from app.resources.personalised_video_invitee.models import PersonalisedVideoInvitee
from app.resources.accounts.models import Account


from queueapp.tasks import celery_app, logger, send_email_actual

@celery_app.task(bind=True, ignore_result=True)
def send_video_link_email(self, result, row_id, *args, **kwargs):
    """
    Sends the video link on the email with token

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the video master
    """
    if result:
        try:
            # first find video
            model = PersonalisedVideoMaster.query.get(row_id)
            if model is None:
                return False
            reply_to = ''

            # generate the email content
            attachment = ""
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']

            invitees = PersonalisedVideoInvitee.query.filter_by(
                video_id=row_id, email_status=False).all()

            account_detail = Account.query.filter_by(row_id=model.account_id).first()

            if model.video_type.lower() == APP.VID_TEASER:
                for invitee in invitees:
                    to_addresses = [invitee.email]
                    # if model.video_type.lower() == APP.VID_TEASER:
                    subject = "Watch Now: Your personalised video demo of ExchangeConnect is ready!"

                    with open('email_html_docs/personalised_video/sample_template.html', 'r') as htmlfile:
                        htmlfile = htmlfile.read()
                    html = htmlfile

                    body = 'Hi {user_name},\r\n' + \
                           'Do you agree that the financial industry needs to adopt ' + \
                           'technology just like every other industry is?' + \
                           '\r\n While we respect the conventional way of how the capital ' + \
                           'markets workflow is carried out, we dared to digitise the entire process. ' + \
                           'We designed a robust technology platform ExchangeConnect that not only ' + \
                           'digitises your capital market workflow but also brings all the stakeholders under one roof.\r\n' + \
                           '\r\n And we pushed ourselves furthermore, by creating ' + \
                           'PERSONALISED DEMO VIDEOS for each of our prospects to truly ' + \
                           'prove how aggressive we are on technology.\r\n' + \
                           '\r\n We have created one for {company_name} as well. ' + \
                           'Here is a link to the teaser video : {link}' + \
                           '\rfor you to get a gist of what are we talking about.\r\n' + \
                           '\r\n If you find this interesting, we would like to send ' + \
                           'you a BESPOKE Video presentation where our founder Pradip Seth ' + \
                           'will personally walk you through how {company_name} will look on ExchangeConnect.\r\n' + \
                           '\r\n We are excited to do this for you, we hope you are too. \r\n' + \
                           '\r\n Looking forward to hearing from you,\n' + \
                           'Team ExchangeConnect'


                    body_dict = {
                        'link': invitee.video_url,
                        'user_name': invitee.first_name,
                        'company_name': account_detail.account_name
                    }
                    html_body = {
                        'link': invitee.video_url,
                        'user_name': invitee.first_name,
                        'company_name': account_detail.account_name
                    }

                    body = body.format(**body_dict)
                    html = html.format(**html_body)

                    bcc_addresses = []

                    send_email_actual(
                        subject=subject, from_name=from_name,
                        keywords=APP.USER_ACTIVITY_EMAIL,
                        bcc_addresses=bcc_addresses,
                        from_email=from_email, to_addresses=to_addresses,
                        reply_to=reply_to, body=body, html=html,
                        attachment=attachment)

                    # APP.EMAIL_SENT
                    invitee.email_status = True
                    db.session.add(invitee)
                    db.session.commit()

                    result = True
            if model.video_type.lower() == APP.VID_DEMO:
                for invitee in invitees:
                    to_addresses = [invitee.email]
                # if model.video_type.lower() == APP.VID_DEMO:
                    subject = "Your video is ready!"

                    with open('email_html_docs/personalised_video/demo_video.html', 'r') as htmlfile:
                        htmlfile = htmlfile.read()
                    html = htmlfile

                    body = "It's here! Your personalised video demo of ExchangeConnect for {company_name} is ready. \r\n" \
                           "Your unique link: {link}\r\n" \
                           "We hope you enjoy viewing this demo as much as we enjoyed creating it for you.\r\n" \
                           "Looking forward to hearing from you,\n" \
                           "Team ExchangeConnect\n" \
                           "PS: Please read the disclaimer carefully.\n"

                    body_dict = {
                        'link': invitee.video_url,
                        'company_name': account_detail.account_name
                    }
                    html_body = {
                        'link': invitee.video_url,
                        'company_name': account_detail.account_name
                    }

                    body = body.format(**body_dict)
                    html = html.format(**html_body)

                    bcc_addresses = []

                    send_email_actual(
                        subject=subject, from_name=from_name,
                        keywords=APP.USER_ACTIVITY_EMAIL,
                        bcc_addresses=bcc_addresses,
                        from_email=from_email, to_addresses=to_addresses,
                        reply_to=reply_to, body=body, html=html,
                        attachment=attachment)

                    # APP.EMAIL_SENT
                    invitee.email_status = True
                    db.session.add(invitee)
                    db.session.commit()

                    result = True

        except Exception as e:
            logger.exception(e)
            result = False

    return result

@celery_app.task(bind=True, ignore_result=True)
def send_invitee_interested_email(self, result, row_id, *args, **kwargs):
    #send invitee interested_email for teaser
    """
    Sends thankyou email for the demo video interest

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the invitee
    """

    if result:
        try:
            # first find invitee details
            model = PersonalisedVideoInvitee.query.get(row_id)
            if model is None:
                return False

            reply_to = ''
            # generate the email content
            attachment = ""
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            to_addresses = [model.email]
            subject = "Your Personalised Video Demo Is On The Way"

            with open('email_html_docs/personalised_video/teaser_interest_user.html', 'r') as htmlfile:
                htmlfile = htmlfile.read()
            html = htmlfile

            video = PersonalisedVideoMaster.query.filter_by(row_id=model.video_id).first()
            if video.account_id:
                account_detail = Account.query.filter_by(row_id=video.account_id).first()

            body = 'Thank you for your interest in our bespoke video demo for ' \
                   '{company_name}. We will send a unique link to you in the ' \
                   'next 3 working days.' \
                   '\r\nPlease note, you will receive a link that can be accessed ' \
                   'only by you.' \
                   '\r\nIf you need more unique links for your colleagues ' \
                   'at {company_name}, please share their work emails and ' \
                   'we will send their unique links to them.' \
                   '\r\nSee you soon!\n' \
                   'Team ExchangeConnect'

            body_dict = {
                'company_name': account_detail.account_name
            }
            body = body.format(**body_dict)
            html = html.format(**body_dict)
            bcc_addresses = []

            send_email_actual(
                subject=subject, from_name=from_name,
                keywords=APP.USER_ACTIVITY_EMAIL,
                bcc_addresses=bcc_addresses,
                from_email=from_email, to_addresses=to_addresses,
                reply_to=reply_to, body=body, html=html,
                attachment=attachment)
            print("account_details: ",account_detail.account_name)

            result = True

        except Exception as e:
            logger.exception(e)
            result = False

        return result


@celery_app.task(bind=True, ignore_result=True)
def send_invitee_interest_sales_email(self, result, row_id, *args, **kwargs):
    # send invitee interested_email to EC sales
    """
    Sends the invitee detail to sales

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the invitee
    """
    if result:
        try:
            model = PersonalisedVideoInvitee.query.get(row_id)
            if model is None:
                return False

            video = PersonalisedVideoMaster.query.filter_by(row_id=model.video_id).first()
            if video.account_id:
                account_detail = Account.query.filter_by(row_id=video.account_id).first()

            reply_to = ''
            # generate the email content
            attachment = ""
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            to_addresses = ['kajal@s-ancial.com']
            subject = "{name} from {company_name} showed interest in personalised demo."

            with open('email_html_docs/personalised_video/sales_invitee_interest.html', 'r+', encoding="utf-8") as htmlfile:
                htmlfile = htmlfile.read()
            html = htmlfile

            body = 'Hi team, ' \
                   '\r\nKudos!' \
                   '\r\n{Name} from {company_name} is interested in receiving the ' \
                   'personalised demo. Please start with the further process.' \
                   '\r\nTarget date: {date}' \
                   '\r\nFingers crossed 🤞' \
                   '\r\nRegards,\n' \
                   'Team ExchangeConnect'

            subject_dict = {
                'name': model.first_name,
                'company_name': account_detail.account_name,
            }

            body_dict = {
                'Name': model.first_name,
                'company_name': account_detail.account_name,
                'date': date.today()
            }
            body = body.format(**body_dict)
            html = html.format(**body_dict)
            subject = subject.format(**subject_dict)
            bcc_addresses = []

            send_email_actual(
                subject=subject, from_name=from_name,
                keywords=APP.USER_ACTIVITY_EMAIL,
                bcc_addresses=bcc_addresses,
                from_email=from_email, to_addresses=to_addresses,
                reply_to=reply_to, body=body, html=html,
                attachment=attachment)

            result = True

        except Exception as e:
            logger.exception(e)
            result = False

        return result


@celery_app.task(bind=True, ignore_result=True)
def send_invitee_not_interested_email(self, result, row_id, *args, **kwargs):
    # send invitee not_interested_email for demo
    """
    Sends Thank you for your time email to the invitee

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the invitee
    """
    if result:
        try:
            # first find invitee details
            model = PersonalisedVideoInvitee.query.get(row_id)
            if model is None:
                return False

            reply_to = ''
            # generate the email content
            attachment = ""
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            to_addresses = [model.email]
            subject = "Thank you for your time | ExchangeConnect"

            #email_html_docs/personalised_video/teaser_not_interested_user.html
            with open('email_html_docs/personalised_video/teaser_not_interested_user.html', 'r') as htmlfile:
                htmlfile = htmlfile.read()
            html = htmlfile

            video = PersonalisedVideoMaster.query.filter_by(row_id=model.video_id).first()
            if video.account_id:
                account_detail = Account.query.filter_by(row_id=video.account_id).first()

            body = 'Hi {user_name},\r\n' \
                   '\r\nThank you for taking out your precious time to look at our teaser.' \
                   '\r\nWe understand that currently you are not interested in checking out ' + \
                   'the personalised video demo we made for {company_name}.' \
                   '\r\nHowever, we really wish you give us an opportunity to share ' +\
                   'how ExchangeConnect can help {company_name} achieve crucial capital market goals. ' \
                   '\r\nIn case you change your mind, please respond to this email and ' +\
                   'we will be more than happy to send you the link.' \
                   '\r\nLooking forward to hearing from you soon.'
            body_dict = {
                'user_name': model.first_name,
                'company_name': account_detail.account_name,
            }
            body = body.format(**body_dict)
            html = html.format(**body_dict)
            bcc_addresses = []

            send_email_actual(
                subject=subject, from_name=from_name,
                keywords=APP.USER_ACTIVITY_EMAIL,
                bcc_addresses=bcc_addresses,
                from_email=from_email, to_addresses=to_addresses,
                reply_to=reply_to, body=body, html=html,
                attachment=attachment)

            result = True
        except Exception as e:
            logger.exception(e)
            result = False

        return result
