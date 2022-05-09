"""
toolkit email body type related helper
"""

from flask import current_app, render_template

from app.common.helpers import generate_event_book_email_link
from app.resources.unsubscriptions.helpers import (
    generate_unsubscribe_email_link)
from app.toolkit_resources.projects import constants as PROJECT


class BaseContent():
    def __init__(self, project):
        self.creator_name = (project.creator.profile.first_name + ' ' +
                             project.creator.profile.last_name)
        self.creator_mail = project.creator.email
        self.project_name = project.project_name
        self.project_type_name = project.project_type.project_type_name
        self.status_code = project.status.code if project.status else None
        self.status_name = project.status.name if project.status else ''
        self.subject = 'Team Design Lab'
        self.context = {
            'project': project,
            'work_area': PROJECT.WORK_ARIA_VERBOSE[project.work_area],
            # 'link': self.login_url,
            'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'creator_name': self.creator_name,
            'project_name': self.project_name}


class OrderPlacedContent(BaseContent):
    """
    email contents for order placed
    """

    def __init__(self, project):
        super(OrderPlacedContent, self).__init__(project)

    def get_creator_content(self):
        """
        generate creator content
        """

        subject, body, attachment, html = '', '', '', ''
        subject = 'Exchange Connect - Your %(order_type)s' +\
                  ' order has been placed'
        subject = subject % {
            'order_type': self.project_type_name}
        html = render_template(
            'toolkit_project/order_placed.html',
            user_name=self.creator_name, **self.context)
        return self.subject, body, attachment, html

    def get_internal_content(self, user_name):
        """
        generate internal (manager, default admin) content
        """

        subject, body, attachment, html = '', '', '', ''
        subject = 'Exchange Connect - %(order_type)s Order received from ' +\
            '%(creator_name)s.'
        subject = subject % {
            'order_type': self.project_type_name,
            'creator_name': self.creator_name}

        html = render_template(
            'toolkit_project/order_placed_internal.html',
            creator_mail=self.creator_mail, user_name=user_name,
            **self.context)

        return self.subject, body, attachment, html


class StatusChangedContent(BaseContent):
    """
    email contents for project status changed.
    """

    def __init__(self, project):

        # self.login_url = generate_event_book_email_link(
        #     current_app.config['ORDER_PLACED_LOGIN_URL'], project)
        super(StatusChangedContent, self).__init__(project)
        self.client_msgs = {
        "general": "The status of your project {} has changed to "
                   "{}. Please log in to Design Lab for "
                   "further details.<br/><br/>Track your project status, make "
                   "iterations and browse our all-in-one library with the "
                   "Design Lab plug-in.".format(
            self.project_name, self.status_name),
        PROJECT.ASSIGNED: "The project has been assigned "
                          "to analyst and/or designer.",
        PROJECT.INTRO_CALL: "Introductory call regarding the project has been done.",
        PROJECT.TEMPLATE_DESIGNING: "Template designing work has been started "
                                    "on your project",
        PROJECT.TEMPLATE_RECV: "Template(s) are available for the project. "
                               "Please review and approve a template "
                               "to proceed further.",
        PROJECT.TEMPLATE_APPROVED: "Template is approved for your project.",
        PROJECT.MAIN_PRESENTATION: "Work on main presentation of your project "
                                   "has been started.",
        PROJECT.PRESENTATION_RECV: "Presentation for your project is available.",
        PROJECT.COMPLETED: "Your project has been successfully completed. "
                           "Feedback regarding our service is highly appreciated."
                           " Thank you!"}
        self.assignee_msgs = {
            "general": "The status of your project {} has changed to "
                       "{}. Please log in to Design Lab for "
                       "further details.<br/><br/>Track your project status, make "
                       "iterations and browse our all-in-one library with the "
                       "Design Lab plug-in.".format(
                self.project_name, self.status_name),
            PROJECT.ASSIGNED: "The project has been assigned "
                              "to analyst and/or designer.",
            PROJECT.INTRO_CALL: "Introductory call regarding the project has been done.",
            PROJECT.TEMPLATE_DESIGNING: "Template designing work has been started "
                                        "on the project",
            PROJECT.TEMPLATE_RECV: "Template(s) are uploaded for the project.",
            PROJECT.TEMPLATE_APPROVED: "The client has approved a Template.",
            PROJECT.MAIN_PRESENTATION: "Work on main presentation of the project "
                                       "has been started.",
            PROJECT.PRESENTATION_RECV: "Presentation(s) are uploaded for the "
                                       "project.",
            PROJECT.COMPLETED: "The project has been successfully completed.",
        }


    def get_creator_content(self):
        """
        generate creator content
        """

        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Update on your project {}'.format(
            self.project_name)
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        html = render_template(
            'toolkit_project/status_changed_client.html',
            msg = self.client_msgs['general'],
            user_name=self.creator_name, **self.context)
        return self.subject, body, attachment, html

    def get_assignee_content(self, user_name):
        """
        generate creator content
        """

        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Update on project assigned ' \
                  'to you - {}'.format(
            self.project_name)
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        html = render_template(
            'toolkit_project/status_changed_assignee.html',
            msg = self.assignee_msgs['general'],
            user_name = user_name, **self.context)
        return self.subject, body, attachment, html

    def get_project_assigned_content(self, assignee_name, admin_name):
        """
        generate analyst/designer content
        """

        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Project assigned - {}'.format(
            self.project_name)
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        html = render_template(
            'toolkit_project/project_assigned.html',
            user_name = assignee_name, admin_name=admin_name, **self.context)
        return self.subject, body, attachment, html

    def get_internal_content(self, assignee_name):
        """
        generate content for admin , account manager
        """

        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Update on the project {}'.format(
            self.project_name)
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        msg = self.assignee_msgs['general']
        html = render_template(
            'toolkit_project/status_changed_assignee.html',
            msg= msg, user_name = assignee_name,**self.context)
        return self.subject, body, attachment, html


class ProjectCancelledContent(BaseContent):
    """
        email contents for cancelled project.
    """

    def __init__(self, project):
        super(ProjectCancelledContent, self).__init__(project)
        self.client_msg = "Your project has been cancelled."
        self.assignee_msg = "A project assigned to you is cancelled."
        self.internal_msg = "A project is cancelled."

    def get_creator_content(self):
        """
        generate cancelled content for creator
        :return:
        """
        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Project cancelled'
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        html = render_template(
            'toolkit_project/project_cancelled.html',
            msg=self.client_msg,
            user_name=self.creator_name, **self.context)
        return self.subject, body, attachment, html

    def get_assignee_content(self, assignee_name):
            """
            generate cancelled content for analyst/designer
            :return:
            """
            subject, body, attachment = '', '', ''
            subject = 'Exchange Connect - Project cancelled'
            # unsubscribe_url = generate_unsubscribe_email_link(email)
            # self.context.update({'unsubscribe': unsubscribe_url})
            html = render_template(
                'toolkit_project/project_cancelled.html',
                msg=self.assignee_msg,
                user_name=assignee_name, **self.context)
            return self.subject, body, attachment, html

    def get_internal_content(self, assignee_name):
        """
        generate cancelled content for admin, manager
        :return:
        """
        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Project cancelled'
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        html = render_template(
            'toolkit_project/project_cancelled.html',
            msg=self.internal_msg,
            user_name=assignee_name, **self.context)
        return self.subject, body, attachment, html


class AnalystRequestedContent(BaseContent):
    """
    email contents for analyst requested
    """

    def __init__(self, project):
        super(AnalystRequestedContent, self).__init__(project)

    def get_internal_content(self, assignee_name):
        """
        generate analyst requested content for admin, manager
        :return:
        """
        subject, body, attachment = '', '', ''
        subject = 'Exchange Connect - Analyst requested ' \
                  'for project - {}'.format(self.project_name)
        # unsubscribe_url = generate_unsubscribe_email_link(email)
        # self.context.update({'unsubscribe': unsubscribe_url})
        html = render_template(
            'toolkit_project/analyst_requested.html',
            user_name=assignee_name, **self.context)
        return self.subject, body, attachment, html


class ProjectApxContent():

    def __init__(self, project):
        self.creator_name = project.first_name + ' ' + project.last_name
        self.creator_mail = project.email
        self.project_name = project.project_name
        self.project_type = project.project_type
        self.subject = 'Team Design Lab'
        self.context = {
            'project': project,
            'work_area': PROJECT.WORK_ARIA_VERBOSE[project.work_area],
            # 'link': self.login_url,
            'helpdesk_number': current_app.config['HELPDESK_NUMBER'],
            'helpdesk_email': current_app.config['HELPDESK_EMAIL'],
            'sign_off_name': current_app.config['DEFAULT_SIGN_OFF_NAME'],
            'project_name': self.project_name}


    def get_creator_content(self):
        """
        generate creator content
        """

        subject, body, attachment, html = '', '', '', ''
        html = render_template(
            'toolkit_project/order_placed_apx.html',
            user_name=self.creator_name, **self.context)
        return self.subject, body, attachment, html
