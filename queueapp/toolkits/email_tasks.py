"""
toolkit project related tasks, for each type of email
"""

from flask import current_app
from sqlalchemy.orm import load_only

from app.common.helpers import generate_event_book_email_link
from app import db, sockio
from app.toolkit_resources.projects.models import Project, ProjectApx
from app.resources.users.models import User
from app.toolkit_resources.projects import constants as PROJECT
from app.resources.notifications import constants as NOTIFY
from app.resources.notifications.schemas import NotificationSchema
from socketapp.base import constants as SOCKETAPP
from app.resources.notifications.helpers import add_notification
from app.resources.roles import constants as ROLE
from app.resources.roles.models import Role
from app.base import constants as APP

from queueapp.tasks import celery_app, logger, send_email_actual
from queueapp.toolkits.email_contents import (
    OrderPlacedContent, StatusChangedContent, ProjectCancelledContent,
    AnalystRequestedContent, ProjectApxContent)


@celery_app.task(bind=True, ignore_result=True)
def send_order_placed_email(self, result, row_id, *args, **kwargs):
    """
    Sends the order placed email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the project/order
    """

    if result:
        try:
            # first find the project/order
            model = Project.query.get(row_id)
            if model is None:
                return False

            # generate the email content
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = OrderPlacedContent(model)
            # login_url = generate_event_book_email_link(
            #     current_app.config['ORDER_PLACED_LOGIN_URL'],
            #     model)

            # send email to creator
            creator_email = model.creator.email
            to_addresses = [creator_email]
            # content for creator
            subject, body, attachment, html = content_getter.\
                get_creator_content()
            send_email_actual(
                subject=subject, keywords=APP.TOOLKIT_EMAIL,
                from_name=from_name, from_email=from_email,
                to_addresses=to_addresses, reply_to=reply_to, body=body,
                html=html, attachment=attachment)
            add_notification(
                user_id=model.creator.row_id,
                account_id=model.creator.account_id,
                notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_CREATED,
                project_id=model.row_id,
                designlab_notification=True)

            # send email to admin, internal contact
            to_address_list = [current_app.config['DEFAULT_ADMIN_EMAILS']]
            manager = model.account.account_manager
            names = ['Team']
            if manager:
                to_address_list.append([manager.manager.email])
                names.append(manager.manager.profile.first_name + ' ' +
                        manager.manager.profile.last_name)

            for name, to_addresses in zip(names, to_address_list):
                # content for admin, internal
                subject, body, attachment, html = content_getter.\
                    get_internal_content(name)

                send_email_actual(
                    subject=subject, keywords=APP.TOOLKIT_EMAIL,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment)
            admins = User.query.join(User.role).filter(
                Role.name==ROLE.ERT_SU).all()
            if manager:
                admins.append(manager.manager)
            for admin in admins:
                add_notification(
                    user_id=admin.row_id,
                    account_id=admin.account_id,
                    notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                    notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_CREATED,
                    project_id=model.row_id)
            result = True

        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_status_change_emails(self, result, row_id, *args, **kwargs):
    """
    Sends the project status changed related emails

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the project/order
    """
    if result:
        try:
            # first find the project/order
            project = Project.query.get(row_id)
            if project is None:
                return False

            # generate the email content
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = StatusChangedContent(project)
            if project.status.code in PROJECT.NOTIFY_CLIENT_STATUSES:
                # send mail to client
                creator_email = project.creator.email
                subject, body, attachment, html = \
                    content_getter.get_creator_content()
                send_email_actual(
                    subject=subject, keywords=APP.TOOLKIT_EMAIL,
                    from_name=from_name, from_email=from_email,
                    to_addresses=[creator_email], reply_to=reply_to, body=body,
                    cc_addresses=[], html=html,
                    attachment=attachment)

                add_notification(
                    user_id=project.creator.row_id,
                    account_id=project.creator.account_id,
                    notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                    notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_STATUS_CHANGED,
                    project_id=project.row_id,
                    project_status_code=project.status.code,
                    designlab_notification=True)
            # for a project with design and content analysts will be
            # communicating and designers will not.If status is changed
            # by action of prime communicator he don't need email notification
            # for knowing that.
            assigness = {
                # prime : project_assignee_relationship
                "prime": 'analysts',
                "non_prime": 'designers',
            }
            if project.work_area == PROJECT.DESIGN:
                assigness["prime"], assigness["non_prime"] = \
                    assigness["non_prime"], assigness["prime"]
            if (project.status.code in
                PROJECT.NOTIFY_PRIME_COMMUNICATOR_STATUSES):
                for prime_user in getattr(project, assigness["prime"]):
                    to_email = prime_user.email
                    user_name = (prime_user.profile.first_name + ' '
                                 + prime_user.profile.last_name)
                    subject, body, attachment, html = \
                        content_getter.get_assignee_content(user_name)
                    send_email_actual(
                        subject=subject, keywords=APP.TOOLKIT_EMAIL,
                        from_name=from_name, from_email=from_email,
                        to_addresses=[to_email], reply_to=reply_to,
                        body=body,
                        cc_addresses=[], html=html,
                        attachment=attachment)
                    add_notification(
                        user_id=prime_user.row_id,
                        account_id=prime_user.account_id,
                        notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                        notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_STATUS_CHANGED,
                        project_id=project.row_id,
                        project_status_code=project.status.code,
                        designlab_notification=True)
            if (project.status.code in
                PROJECT.NOTIFY_NON_PRIME_COMMUNICATOR_STATUSES):
                for non_prime_user in getattr(project, assigness["non_prime"]):
                    to_email = non_prime_user.email
                    user_name = (non_prime_user.profile.first_name + ' '
                                 + non_prime_user.profile.last_name)
                    subject, body, attachment, html = \
                        content_getter.get_assignee_content(user_name)
                    send_email_actual(
                        subject=subject, keywords=APP.TOOLKIT_EMAIL,
                        from_name=from_name, from_email=from_email,
                        to_addresses=[to_email], reply_to=reply_to,
                        body=body,
                        cc_addresses=[], html=html,
                        attachment=attachment)
                    add_notification(
                        user_id=non_prime_user.row_id,
                        account_id=non_prime_user.account_id,
                        notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                        notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_STATUS_CHANGED,
                        project_id=project.row_id,
                        project_status_code=project.status.code,
                        designlab_notification=True)

            # send email to admin, internal contact
            to_address_list = [current_app.config['DEFAULT_ADMIN_EMAILS']]
            manager = project.account.account_manager
            names = ['Team']
            if manager:
                to_address_list.append([manager.manager.email])
                names.append(manager.manager.profile.first_name + ' ' +
                             manager.manager.profile.last_name)

            for name, to_addresses in zip(names, to_address_list):
                # content for admin, internal
                subject, body, attachment, html = content_getter. \
                    get_internal_content(name)

                send_email_actual(
                    subject=subject, keywords=APP.TOOLKIT_EMAIL,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to, body=body,
                    html=html, attachment=attachment)
            admins = User.query.join(User.role).filter(
                Role.name == ROLE.ERT_SU).all()
            if manager:
                admins.append(manager.manager)
            for admin in admins:
                add_notification(
                    user_id=admin.row_id,
                    account_id=admin.account_id,
                    notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                    notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_STATUS_CHANGED,
                    project_id=project.row_id,
                    project_status_code=project.status.code)
            result = True
        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_project_assigned_emails(
        self, result, project_id, admin_id, analyst_ids=[], designer_ids=[],
        *args, **kwargs):
    """
    Sends the project assigned emails

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param project_id:
        the row id of the project/order
    :param analyst_ids:
        list of newly assigned analyst user ids
    :param designer_ids:
        list of newly assigned designer ids
    """
    if result:
        try:
            # first find the project/order
            project = Project.query.get(project_id)
            if project is None:
                return False
            assigned_users = User.query.filter(
                User.row_id.in_(analyst_ids+designer_ids)).options(
                load_only(User.row_id, User.email)).all()
            admin_user = User.query.get(admin_id)
            admin_name = admin_user.profile.first_name + ' ' \
                         + admin_user.profile.last_name
            # generate the email content
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = StatusChangedContent(project)
            for each in assigned_users:
                assignee_name = (each.profile.first_name + ' '
                                 + each.profile.last_name)
                # send mail to client
                assignee_email = each.email
                subject, body, attachment, html = \
                    content_getter.get_project_assigned_content(
                        assignee_name, admin_name)
                send_email_actual(
                    subject=subject, keywords=APP.TOOLKIT_EMAIL,
                    from_name=from_name, from_email=from_email,
                    to_addresses=[assignee_email], reply_to=reply_to, body=body,
                    cc_addresses=[], html=html,
                    attachment=attachment)
                # add notification to user
                add_notification(
                    user_id=each.row_id, account_id=each.account_id,
                    notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                    notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_ASSIGNED,
                    project_id=project.row_id,
                    designlab_notification=True)

            result = True

        except Exception as e:
            logger.exception(e)
            result = False

    return result


@celery_app.task(bind=True, ignore_result=True)
def send_project_cancelled_emails(self, result, project_id, *args, **kwargs):
    if result:
        """
        sends project cancelled emails
        :param self:
        :param result: Boolean
        :param project_id: int
        :param args:
        :param kwargs:
        :return:
        """
        try:
            project = Project.query.get(project_id)
            if not project:
                return False

            # generate the email content
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = ProjectCancelledContent(project)
            # send mail to client
            creator_email = project.creator.email
            subject, body, attachment, html = \
                content_getter.get_creator_content()
            send_email_actual(
                subject=subject, keywords=APP.TOOLKIT_EMAIL,
                from_name=from_name, from_email=from_email,
                to_addresses=[creator_email], reply_to=reply_to, body=body,
                cc_addresses=[], html=html,
                attachment=attachment)
            add_notification(
                user_id=project.creator.row_id,
                account_id=project.creator.account_id,
                notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_CANCELLED,
                project_id=project.row_id,
                designlab_notification=True)

            # send mail to assignees
            for each in project.analysts + project.designers:
                to_email = each.email
                user_name = (each.profile.first_name + ' '
                             + each.profile.last_name)
                subject, body, attachment, html = \
                    content_getter.get_assignee_content(user_name)
                send_email_actual(
                    subject=subject, keywords=APP.TOOLKIT_EMAIL,
                    from_name=from_name, from_email=from_email,
                    to_addresses=[to_email], reply_to=reply_to,
                    body=body,
                    cc_addresses=[], html=html,
                    attachment=attachment)
                add_notification(
                    user_id=each.row_id, account_id=each.account_id,
                    notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                    notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_CANCELLED,
                    project_id=project.row_id,
                    designlab_notification=True)

            # send email to admin, internal contact
            to_address_list = [current_app.config['DEFAULT_ADMIN_EMAILS']]
            manager = project.account.account_manager
            names = ['Team']
            if manager:
                to_address_list.append([manager.manager.email])
                names.append(manager.manager.profile.first_name + ' ' +
                             manager.manager.profile.last_name)

            for name, to_addresses in zip(names, to_address_list):
                # content for admin, internal
                subject, body, attachment, html = content_getter. \
                    get_internal_content(name)

                send_email_actual(
                    subject=subject, keywords=APP.TOOLKIT_EMAIL,
                    from_name=from_name, from_email=from_email,
                    to_addresses=to_addresses, reply_to=reply_to,
                    body=body,
                    html=html, attachment=attachment)
            admins = User.query.join(User.role).filter(
                Role.name == ROLE.ERT_SU).all()
            if manager:
                admins.append(manager.manager)
            for admin in admins:
                add_notification(
                    user_id=admin.row_id,
                    account_id=admin.account_id,
                    notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                    notify_type=NOTIFY.NT_DESIGNLAB_PROJECT_CANCELLED,
                    project_id=project.row_id)
            result = True

        except Exception as e:
            logger.exception(e)
            result = False


@celery_app.task(bind=True, ignore_result=True)
def send_analyst_requested_emails(self, result, project_id, *args, **kwargs):
    """
    sends analyst requested emails and notifications
    :param self:
    :param result: boolean
    :param project_id: int
    :param args:
    :param kwargs:
    :return:
    """
    if not result:
        return
    try:
        project = Project.query.get(project_id)
        if not project:
            return False
        # generate the email content
        from_name = current_app.config['DEFAULT_SENDER_NAME']
        from_email = current_app.config['DEFAULT_SENDER_EMAIL']
        reply_to = ''

        # initialize
        content_getter = AnalystRequestedContent(project)
        # send email to admin, internal contact
        to_address_list = [current_app.config['DEFAULT_ADMIN_EMAILS']]
        manager = project.account.account_manager
        names = ['Team']
        if manager:
            to_address_list.append([manager.manager.email])
            names.append(manager.manager.profile.first_name + ' ' +
                         manager.manager.profile.last_name)

        for name, to_addresses in zip(names, to_address_list):
            # content for admin, internal
            subject, body, attachment, html = content_getter. \
                get_internal_content(name)

            send_email_actual(
                subject=subject, keywords=APP.TOOLKIT_EMAIL,
                from_name=from_name, from_email=from_email,
                to_addresses=to_addresses, reply_to=reply_to,
                body=body,
                html=html, attachment=attachment)
        admins = User.query.join(User.role).filter(
            Role.name == ROLE.ERT_SU).all()
        if manager:
            admins.append(manager.manager)
        for admin in admins:
            add_notification(
                user_id=admin.row_id,
                account_id=admin.account_id,
                notify_grp=NOTIFY.NGT_DESIGN_LAB_PROJECT,
                notify_type=NOTIFY.NT_DESIGNLAB_ANALYST_REQUESTED,
                project_id=project.row_id)
    except Exception as e:
        logger.exception(e)
        return False


@celery_app.task(bind=True, ignore_result=True)
def send_order_placed_email_apx(self, result, row_id, *args, **kwargs):
    """
    Sends the order placed email

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param row_id:
        the row id of the project/order
    """

    if result:
        try:
            # first find the project/order
            model = ProjectApx.query.get(row_id)
            if model is None:
                return False

            # generate the email content
            from_name = current_app.config['DEFAULT_SENDER_NAME']
            from_email = current_app.config['DEFAULT_SENDER_EMAIL']
            reply_to = ''

            # initialize
            content_getter = ProjectApxContent(model)
            # login_url = generate_event_book_email_link(
            #     current_app.config['ORDER_PLACED_LOGIN_URL'],
            #     model)

            # send email to creator
            creator_email = model.email
            to_addresses = [creator_email]
            bcc_addresses = current_app.config['DEVELOPER_EMAILS']
            # content for creator
            subject, body, attachment, html = content_getter.\
                get_creator_content()
            send_email_actual(
                subject=subject, keywords=APP.TOOLKIT_EMAIL,
                from_name=from_name, from_email=from_email,
                to_addresses=to_addresses, reply_to=reply_to, body=body,
                html=html, attachment=attachment, bcc_addresses=bcc_addresses)

        except Exception as e:
            logger.exception(e)
            result = False

    return result