"""
Helpdesk related tasks
"""

from flask import current_app

from app.helpdesk_resources.help_tickets.models import HelpTicket
from app.helpdesk_resources.help_comments.models import HelpComment

from queueapp.tasks import celery_app, logger, send_email_actual
from app.base import constants as APP


@celery_app.task(bind=True, ignore_result=True)
def send_helpdesk_email(self, result, ticket_id, comment_id=None, status=False,
                        *args, **kwargs):
    """
    #TODO: will change in next iteration, for now adding format here.

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param ticket_id:
        the ticket id
    :param comment_id:
        the comment id
    :param status:
        whether this is a status changed email
    """
    if result:
        try:
            ticket = HelpTicket.query.get(ticket_id)
            if ticket is None or ticket.deleted:
                logger.exception('HelpTicket not found or deleted')
                return True
            ticket.load_urls(expires_in=86400)

            # check if comment email
            comment = None
            if comment_id:
                comment = HelpComment.query.get(comment_id)
                if comment is None or comment.deleted:
                    logger.exception('HelpComment not found or deleted')
                    return True
                comment.load_urls(expires_in=86400)

            to_addresses = [ticket.email]
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''
            subject = '%(brand_name)s Support – Query generated ' + \
                      str(ticket_id)
            subject = subject % {
                'brand_name': current_app.config['BRAND_NAME']}
            html = ''
            attachment = ''
            url_attachment = ''
            body = 'Hi %(user_name)s,\r\n\r\n' + \
                   'Thank you for choosing %(brand_name)s.\r\n'
            if status:
                body += 'The status of the ticket: ' + str(ticket_id) +\
                    ', has been changed to: "' + ticket.status.title() + '"'
            elif not comment:
                # ticket only email
                body += 'New ticket for your query has been generated: ' + \
                        str(ticket_id) + '\r\n\r\n'
                body += 'Name: ' + ticket.name + '\r\n'
                body += 'Email: ' + ticket.email + '\r\n'
                body += 'Phone: ' + ticket.phone + '\r\n'
                body += 'Section: ' + ticket.section.title() + '\r\n'
                body += 'Function: ' + ticket.function.title() + '\r\n'
                body += 'Subject: ' + ticket.subject + '\r\n'
                body += 'Description: ' + ticket.description + '\r\n\r\n'
                if ticket.attachment:
                    url_attachment = ticket.attachment_url
            else:
                # comment email
                body += 'New comment added to ticket: ' + str(ticket_id) +\
                    '\r\n\r\n' +\
                    'Message: "' + comment.message + '"\r\n'
                if comment.attachment:
                    url_attachment = comment.attachment_url
            if url_attachment:
                body += 'Attachment: ' + url_attachment

            body += 'Please let us know if you have any queries by ' + \
                'emailing us on %(helpdesk_email)s or call us on ' + \
                '%(helpdesk_number)s.\r\n\r\nThank You,\r\n' + \
                '%(sign_off_name)s'
            body = body % {
                'brand_name': current_app.config['BRAND_NAME'],
                'user_name': ticket.creator.profile.first_name,
                'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
                'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
                'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME']}
            # send user email
            send_email_actual(
                subject=subject, from_name=from_name, from_email=from_email,
                keywords=APP.HELPDESK_EMAIL,
                to_addresses=to_addresses, reply_to=reply_to, body=body,
                html=html, attachment=attachment)
            # send admin email
            send_email_actual(
                subject=subject, from_name=from_name, from_email=from_email,
                keywords=APP.HELPDESK_EMAIL,
                to_addresses=current_app.config['HELPDESK_ADMIN_EMAILS'],
                reply_to=reply_to, body=body, html=html, attachment=attachment)
            result = True
        except Exception as e:
            raise e
            logger.exception(e)
            result = False

    return result
