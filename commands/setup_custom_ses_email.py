import datetime

from flask import current_app
from flask_script import Command, Option

from app.common.utils import get_aws_session
from config import (
    DEFAULT_SENDER_EMAIL, BRAND_NAME, SES_CUSTOM_TEMPLATE_SUCCESS_URL,
    SES_CUSTOM_TEMPLATE_FAILURE_URL)


class CustomTemplateDefaults(object):

    from_email_address = DEFAULT_SENDER_EMAIL
    template_subject = 'Please confirm your email address'
    template_content = '<html><head></head>' +\
        '<body style="font-family:sans-serif;">' +\
        '<h1 style="text-align:center">Ready to start sending ' +\
        'email with ' + BRAND_NAME + '?</h1>' +\
        '<p>We here at ' + BRAND_NAME + ' are happy to have you on ' +\
        'board! There\'s just one last step to complete before' +\
        'you can start sending email. Just click the following ' +\
        'link to verify your email address. Once we confirm that ' +\
        'you\'re really you, we\'ll give you some additional ' +\
        'information to help you get started with ' + BRAND_NAME + '.</p>' +\
        '</body></html>'
    success_redirection_url = SES_CUSTOM_TEMPLATE_SUCCESS_URL
    failure_redirection_url = SES_CUSTOM_TEMPLATE_FAILURE_URL


class CreateCustomSESVerificationTemplate(Command, CustomTemplateDefaults):
    """
    Command to create the custom ses verification template

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Creating the template...')

        try:
            client = get_aws_session(
                client_name='ses', region_name=current_app.config[
                    'AWS_SES_REGION'])
            response = client.create_custom_verification_email_template(
                TemplateName=current_app.config['SES_CUSTOM_TEMPLATE'],
                FromEmailAddress=self.from_email_address,
                TemplateSubject=self.template_subject,
                TemplateContent=self.template_content,
                SuccessRedirectionURL=self.success_redirection_url,
                FailureRedirectionURL=self.failure_redirection_url)

            if (not response or 'ResponseMetadata' not in response or
                    'RequestId' not in response['ResponseMetadata'] or
                    response['ResponseMetadata']['HTTPStatusCode'] != 200):
                print('Error')
                print(response)
                exit(1)

            response2 = client.get_custom_verification_email_template(
                TemplateName=current_app.config['SES_CUSTOM_TEMPLATE'])
            if not response2 or 'TemplateName' not in response2:
                print('Error')
                print(response2)
                exit(1)

        except Exception as e:
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')


class UpdateCustomSESVerificationTemplate(Command, CustomTemplateDefaults):
    """
    Command to create the custom ses verification template

    :arg verbose:
        print progress
    :arg dry:
        dry run
    """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
        Option('--template_name', '-template_name', dest='template_name'),
        Option('--from_address', '-from_address', dest='from_address'),
        Option('--subject', '-subject', dest='subject'),
        Option('--content', '-content', dest='content'),
        Option('--success_url', '-success_url', dest='success_url'),
        Option('--failure_url', '-failure_url', dest='failure_url'),
    ]

    def run(self, verbose, dry, template_name, from_address, subject, content,
            success_url, failure_url):

        template_name = template_name or current_app.config[
            'SES_CUSTOM_TEMPLATE']
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('Updating the template...' + template_name)

        from_address = from_address or self.from_email_address
        subject = subject or self.template_subject
        content = content or self.template_content
        success_url = success_url or self.success_redirection_url
        failure_url = failure_url or self.failure_redirection_url

        try:
            client = get_aws_session(
                client_name='ses', region_name=current_app.config[
                    'AWS_SES_REGION'])
            response = client.update_custom_verification_email_template(
                TemplateName=template_name, FromEmailAddress=from_address,
                TemplateSubject=subject, TemplateContent=content,
                SuccessRedirectionURL=success_url,
                FailureRedirectionURL=failure_url)

            if (not response or 'ResponseMetadata' not in response or
                    'RequestId' not in response['ResponseMetadata'] or
                    response['ResponseMetadata']['HTTPStatusCode'] != 200):
                print('Error')
                print(response)
                exit(1)

            response2 = client.get_custom_verification_email_template(
                TemplateName=template_name)
            if not response2 or 'TemplateName' not in response2:
                print('Error')
                print(response2)
                exit(1)

        except Exception as e:
            print(e)
            exit(1)

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
