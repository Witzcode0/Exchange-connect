# import datetime

import requests
from datetime import datetime, timezone, timedelta

from flask import Markup
from flask_script import Command, Option
from flask import render_template
from sqlalchemy.orm import load_only
from sqlalchemy import and_, or_, func
from flask import current_app
from sqlalchemy import and_, func
from copy import deepcopy

from app.common.utils import time_converter
from app.resources.bse.models import BSEFeed
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from queueapp.tasks import send_email_actual
from app.base import constants as CONST
from app.common.helpers import generate_event_book_email_link, generate_bse_announcement_email_link
from app import db, flaskapp
from app.resources.users.models import User
from app.resources.user_profiles.models import UserProfile
from app.resources.follows.models import CFollow
from app.resources.news.models import (NewsItem, newsaccounts, TopNews)
from app.resources.accounts.models import Account, AccountPeerGroup
from app.resources.corporate_announcements.models import CorporateAnnouncement
from app.resources.company_news_announcements.models import NewsAnnouncements
from app.market_resources.market_comment.models import MarketAnalystComment
from app.market_resources.market_performance.models import MarketPerformance
from app.resources.accounts import constants as ACCOUNT
from app.domain_resources.domains.models import Domain
from app.resources.unsubscriptions.helpers import (
    generate_unsubscribe_email_link, is_unsubscription)
from app.news_letter.distribution_list.models import DistributionList
from app.news_letter.email_logs.models import Emaillogs
from app.news_letter.email_logs import constants as CHOICE


def suffix(d):
    return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

class SendBseAnnouncementEmail(Command):
    """
    Command to send bse announcements

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

        subject = "Announcement updates from ExchangeConnect"

        from_name = current_app.config['DEFAULT_UPDATE_NAME']
        from_email = current_app.config['DEFAULT_UPDATE_EMAIL']
        bcc_addresses = ['vrushabh@s-ancial.com', 'kajal@s-ancial.com']

        utc_now = datetime.now(timezone.utc)

        today_start = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(hours=23, minutes=59, seconds=59)

        email_log_list = []
        # users = []

        # query = db.session.query(BSEFeed.account_id, CFollow.sent_by)\
        #     .join(CFollow, BSEFeed.account_id == CFollow.company_id)\
        #     .join(Account, BSEFeed.account_id == Account.row_id)\
        #     .join(User, CFollow.sent_by == User.row_id)\
        #     .join(CorporateAnnouncementCategory, BSEFeed.ec_category == CorporateAnnouncementCategory.row_id)\
        #     .filter(and_(BSEFeed.created_date >= today_start, BSEFeed.created_date <= today_end,
        #                  Account.account_type == ACCOUNT.ACCT_CORPORATE,
        #                  User.deleted.is_(False), User.deactivated.is_(False))).all()

        # for account_id, user_id in query:
        #     if user_id in users:
        #         continue
        #     users.append(user_id)
        users = [46, 614]

        for each_user in users:
            email_data = {}
            announcements = []
            full_announcements = []

            all_announcements = db.session.query(
                BSEFeed.row_id, BSEFeed.head_line, CFollow.sent_by,
                Account.account_name, BSEFeed.type_of_announce, BSEFeed.dt_tm,
                BSEFeed.account_id, CorporateAnnouncementCategory.name)\
                .join(CFollow, BSEFeed.account_id == CFollow.company_id) \
                .join(Account, BSEFeed.account_id == Account.row_id) \
                .join(CorporateAnnouncementCategory, BSEFeed.ec_category == CorporateAnnouncementCategory.row_id)\
                .filter(and_(BSEFeed.created_date >= today_start,
                BSEFeed.created_date <= today_end,
                Account.account_type == ACCOUNT.ACCT_CORPORATE,
                CFollow.sent_by == each_user)).all()

            for announcement in all_announcements:
                announcement_dict = {}
                '''
                announcement[0] = BSEFeed row_id
                announcement[1] = BSEFeed Headline
                announcement[2] = CFollow sent_by
                announcement[3] = Account account_name
                announcement[4] = BSEFeed type_of_announce
                announcement[5] = BSEFeed dt_tm
                announcement[6] = BSEFeed account_id
                announcement[7] = CorporateAnnouncementCategory name
                '''
                if announcement[7].lower() == 'Annual Report'.lower():
                    announcement_dict['announcement_category'] = announcement[7]
                elif announcement[7].lower() == 'Shareholder Meeting'.lower():
                    announcement_dict['announcement_category'] = announcement[7]
                elif announcement[7].lower() == 'Board Meeting'.lower():
                    announcement_dict['announcement_category'] = announcement[7]
                elif announcement[7].lower() == 'Analyst/ Investor Meet & Presentation'.lower():
                    announcement_dict['announcement_category'] = announcement[7]
                else:
                    continue
                announcement_dict['company_name'] = announcement[3]
                announcement_dict['head_line'] = announcement[1]
                # Convert UTC to IST
                ist_time = time_converter(announcement[5], current_app.config['USER_DEFAULT_TIMEZONE'],
                                          current_app.config['SYSTEM_TIMEZONE'])
                time = ist_time.strftime("%H:%M")
                converted_time = datetime.strptime(time, "%H:%M").strftime("%I:%M %p")
                announcement_dict['date_time'] = announcement[5].strftime("%d/%m/%Y") + ' ' + converted_time
                # Generate announcement url
                url = generate_bse_announcement_email_link(
                    current_app.config[
                        'BSE_ANNOUNCEMENT_JOIN_ADD_URL'],
                    announcement)
                announcement_dict['url'] = url
                announcements.append(announcement_dict)

            if announcements and len(announcements) < 10:
                email_data['announcements'] = announcements
            else:
                if len(announcements) > 10:
                    # Generate announcement list by priority
                    for each_announcement in announcements:
                        if 'announcement_category' in each_announcement and len(full_announcements) < 10:
                            if each_announcement['announcement_category'].lower() == 'annual report':
                                full_announcements.append(each_announcement)
                    if len(full_announcements) < 10:
                        for each_announcement in announcements:
                            if 'announcement_category' in each_announcement and len(full_announcements) < 10:
                                if each_announcement['announcement_category'].lower() == 'shareholder meeting':
                                    full_announcements.append(each_announcement)
                    if len(full_announcements) < 10:
                        for each_announcement in announcements:
                            if 'announcement_category' in each_announcement and len(full_announcements) < 10:
                                if each_announcement['announcement_category'].lower() == 'board meeting':
                                    full_announcements.append(each_announcement)
                    if len(full_announcements) < 10:
                        for each_announcement in announcements:
                            if 'announcement_category' in each_announcement and len(full_announcements) < 10:
                                if each_announcement['announcement_category'].lower() == 'analyst/ investor meet & presentation':
                                    full_announcements.append(each_announcement)
                    email_data['announcements'] = full_announcements
                else:
                    continue

            html = render_template(
                'bse_announcements_template.html',
                companies=email_data)

            user = db.session.query(User).filter(and_(
                    User.row_id == each_user,
                    User.deleted.is_(False), User.deactivated.is_(False))).first()
            if user:
                if is_unsubscription(user.email, CONST.EVNT_BSE_FEED):
                    # add log for UNSUBSCRIBE
                    un_dict = {}
                    if isinstance(user, User):
                        un_dict['user_id'] = user.row_id
                        un_dict['dist_user_id'] = None
                    else:
                        un_dict['user_id'] = None
                        un_dict['dist_user_id'] = user.row_id
                    un_dict['email_sent'] = CHOICE.UNSUBSCRIBE
                    # Only indian domain will receive this email
                    # So, doamin_id = 1
                    un_dict['domain_id'] = 1
                    email_log_list.append(un_dict)

                    # add log from dict to model
                    if len(email_log_list) >= 100:
                        for log in email_log_list:
                            email_inst = Emaillogs(email_sent=log['email_sent'],
                                user_id=log['user_id'], dist_user_id=log['dist_user_id'],
                                domain_id=log['domain_id'])
                            db.session.add(email_inst)
                            db.session.commit()
                        email_log_list = []
                    continue

                if isinstance(user, User):
                    user_name = user.profile.first_name if len(
                        user.profile.first_name.replace(".", "").replace(
                            " ", "").strip()) >= 3 else user.profile.last_name
                else:
                    user_name = user.first_name if len(
                        user.first_name.replace(".", "").replace(
                            " ", "").strip()) >= 3 else user.last_name

                unsubscribe_url = generate_unsubscribe_email_link(
                    user.email)
                user_data = {'unsubscribe': unsubscribe_url,
                            'user_name': user_name}
                final_html = html.format(**user_data)

                if 'announcements' in email_data.keys():
                    un_dict = {}
                    if isinstance(user, User):
                        un_dict['user_id'] = user.row_id
                        un_dict['dist_user_id'] = None
                        # Only indian domain will receive this email
                        # So, doamin_id = 1
                        un_dict['domain_id'] = 1
                    else:
                        un_dict['user_id'] = None
                        un_dict['dist_user_id'] = user.row_id
                        un_dict['domain_id'] = 1
                try:
                    send_email_actual(
                        subject=subject, keywords=CONST.DAILY_ANNOUNCEMENT,
                        from_name=from_name, from_email=from_email,
                        to_addresses=[user.email], bcc_addresses=bcc_addresses,
                        html=final_html)

                    # add email log (SENT)
                    un_dict['email_sent'] = CHOICE.SENT
                    email_log_list.append(un_dict)
                except:
                    # add email log (NOT SENT)
                    un_dict['email_sent'] = CHOICE.NOT_SENT
                    email_log_list.append(un_dict)

                if len(email_log_list) >= 100:
                    for log in email_log_list:
                        email_inst = Emaillogs(email_sent=log['email_sent'],
                            user_id=log['user_id'], dist_user_id=log['dist_user_id'],
                            domain_id=log['domain_id'])
                        db.session.add(email_inst)
                        db.session.commit()
                    email_log_list = []
            else:
                continue

        # add log from dict to model
        for log in email_log_list:
            email_inst = Emaillogs(email_sent=log['email_sent'],
                user_id=log['user_id'],dist_user_id=log['dist_user_id'],
                domain_id=log['domain_id'])
            db.session.add(email_inst)
            db.session.commit()

        print('---' + str(datetime.utcnow()) + '---')
        print('Done')
