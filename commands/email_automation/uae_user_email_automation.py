import datetime
import requests

from flask import Markup
from flask_script import Command, Option
from flask import render_template
from sqlalchemy.orm import load_only
from sqlalchemy import and_, or_, func
from flask import current_app
from sqlalchemy import and_, func
from copy import deepcopy

from queueapp.tasks import send_email_actual
from app.base import constants as CONST
from app.common.helpers import generate_event_book_email_link
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

class SendUAENewsEmail(Command):
    """
    Command to send news and announcements

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
        # Option('--domain_id', '-domain_id', dest='domain_id', 
        #        default=False, required=True)
    ]

    def run(self, verbose, dry):

        from_name = current_app.config['DEFAULT_UAE_UPDATE_NAME']
        from_email = current_app.config['DEFAULT_UAE_UPDATE_EMAIL']
        bcc_addresses = current_app.config['NEWSLETTER_UAE_BCC_ADDRESS']

        dict_account = DistributionList.query.join(
            Account, Account.row_id==DistributionList.account_id).filter(
            Account.domain_id == 4).distinct(DistributionList.account_id).all()
        account_arr = [dict_id.account_id for dict_id in dict_account]

        accounts = db.session.query(Account).filter(and_(Account.row_id.in_(account_arr),
            Account.domain_id == 4)).options(load_only(
                'row_id', 'account_name')).all()

        # market comment
        comment = None
        market_comment = db.session.query(MarketAnalystComment).join(
            NewsAnnouncements, MarketAnalystComment.row_id ==
            NewsAnnouncements.market_comment_id).filter(and_(
            func.date(
                NewsAnnouncements.created_date) ==
            datetime.datetime.now().date(),
            MarketAnalystComment.domain_id == 4)).order_by(
            MarketAnalystComment.row_id.desc()).first()
        if market_comment:
            comment = Markup(market_comment.comment)

        if market_comment.subject:
            subject = market_comment.subject
        else:
            subject = "Daily Dots: Your personalised market updates, powered by ExchangeConnect"

        email_log_list = []
        default_news_list = []
        for account in accounts:

            email_data = {}
            # announcements = []
            news_list = []

            total_news = 0
            view_more = False

            default_news = []
            topnews = TopNews.query.filter(
                and_(
                    TopNews.date == datetime.datetime.now().date(),
                    TopNews.domain_id == account.domain_id)).first()
            if topnews:
                news_ids = topnews.news_ids
                for news_id in NewsItem.query.filter(
                    NewsItem.row_id.in_(news_ids)).all():
                    news = {}
                    news['href'] = news_id.link
                    news['title'] = news_id.title
                    news['url'] = news_id.image_url
                    default_news.append(news)

            news_list = default_news
            if len(news_list) > 12 :
                view_more = True

            # list of announcements
            # all_announcements = db.session.query(
            #     CorporateAnnouncement).join(NewsAnnouncements,
            #                                 CorporateAnnouncement.row_id ==
            #                                 NewsAnnouncements.announcements_id).filter(
            #     and_(
            #         NewsAnnouncements.account_id == account.row_id,
            #         func.date(
            #             NewsAnnouncements.created_date) ==
            #         datetime.datetime.now().date())).options(load_only('row_id', 'subject')
            #                                                  ).all()
            # event_url = generate_event_book_email_link(
            #     current_app.config[
            #         'CORPORATE_ANNOUNCEMENT_JOIN_ADD_URL'],
            #     account,
            #     domain_name=account.domain.name)
            # for announcement in all_announcements:
            #     if announcement.subject:
            #         announcement_dict = {}
            #         announcement_dict['company_name'] = account.account_name
            #         announcement_dict['subject'] = announcement.subject
            #         announcement_dict['url'] = event_url
            #         announcements.append(announcement_dict)

            if news_list:
                email_data['news'] = news_list
            # if announcements:
            #     email_data['announcements'] = announcements

            email_data['view_more'] = view_more
            if comment:
                email_data['comment'] = comment
            email_data["user_company"] = account.account_name
            # todo: maybe used in future
            email_data['current_day'] = datetime.datetime.now().day
            email_data['current_suffix'] = suffix(datetime.datetime.now().day)
            email_data['current_month'] = datetime.datetime.now().strftime("%B")
            email_data['current_year'] = datetime.datetime.now().year
            # load render for particular Account
            html = render_template(
                'company_news_announcements_template_uae.html',
                companies=email_data)
            
            # users = db.session.query(User).filter(and_(
            #     User.account_id == account.row_id,
            #     User.deleted.is_(False), User.deactivated.is_(False))).all()
            dict_user = db.session.query(DistributionList).filter(
                DistributionList.account_id == account.row_id).all()

            users = dict_user

            for user in users:
                if is_unsubscription(user.email,CONST.EVNT_NEWS_LETTER):
                    # add log for UNSUBSCRIBE
                    un_dict = {}
                    if isinstance(user,User):
                        un_dict['user_id'] = user.row_id
                        un_dict['dist_user_id'] = None
                    else:
                        un_dict['user_id'] = None
                        un_dict['dist_user_id'] = user.row_id
                    un_dict['email_sent'] = CHOICE.UNSUBSCRIBE
                    un_dict['domain_id'] = account.domain_id
                    email_log_list.append(un_dict)

                    # add log from dict to model
                    if len(email_log_list) >= 100:
                        for log in email_log_list:
                            email_inst = Emaillogs(email_sent=log['email_sent'],
                                user_id=log['user_id'],dist_user_id=log['dist_user_id'],
                                domain_id=log['domain_id'])
                            db.session.add(email_inst)
                            db.session.commit()
                        email_log_list = []
                    continue

                if isinstance(user,User):
                    user_name = user.profile.first_name if len(
                        user.profile.first_name.replace(".", "").replace(
                            " ", "").strip()) >= 3 else user.profile.last_name
                else:
                    user_name = user.first_name if len(
                        user.first_name.replace(".", "").replace(
                            " ", "").strip()) >= 3 else user.last_name

                unsubscribe_url = generate_unsubscribe_email_link(
                    user.email,4)

                user_data = {'unsubscribe': unsubscribe_url,
                             'user_name': user_name
                             }
                final_html = html.format(**user_data)
                # send mail
                if 'comment' in email_data.keys() or (
                    'news' in email_data.keys()):
                    un_dict = {}
                    if isinstance(user,User):
                        un_dict['user_id'] = user.row_id
                        un_dict['dist_user_id'] = None
                        un_dict['domain_id'] = account.domain_id
                    else:
                        un_dict['user_id'] = None
                        un_dict['dist_user_id'] = user.row_id
                        un_dict['domain_id'] = account.domain_id

                    try:
                        send_email_actual(
                            subject=subject, keywords=CONST.DAILY_NEWSLETTER,
                            from_name=from_name, from_email=from_email,
                            to_addresses=[user.email], bcc_addresses=bcc_addresses,
                            html=final_html)

                        # add email log (SENT)
                        un_dict['email_sent'] = CHOICE.SENT
                        email_log_list.append(un_dict)
                        # email_log_list.append({"email":user.email,"email_sent":CHOICE.SENT})

                    except:
                        # add email log (NOT SENT)
                        un_dict['email_sent'] = CHOICE.NOT_SENT
                        email_log_list.append(un_dict)
                        # email_log_list.append({"email":user.email,"email_sent":CHOICE.NOT_SENT})

                if len(email_log_list) >= 100:
                    for log in email_log_list:
                        email_inst = Emaillogs(email_sent=log['email_sent'],
                            user_id=log['user_id'],dist_user_id=log['dist_user_id'],
                            domain_id=log['domain_id'])
                        db.session.add(email_inst)
                        db.session.commit()
                    email_log_list = []

        # add today date and current year in html template
        # TODO: maybe used in future
        '''def suffix(d):
            return 'th' if 11 <= d <= 13 else {1: 'st', 2: 'nd',
                                               3: 'rd'}.get(d % 10,
                                                            'th')'''
        # add log from dict to model
        for log in email_log_list:
            email_inst = Emaillogs(email_sent=log['email_sent'],
                user_id=log['user_id'],dist_user_id=log['dist_user_id'],
                domain_id=log['domain_id'])
            db.session.add(email_inst)
            db.session.commit()

        print('---' + str(datetime.datetime.utcnow()) + '---')
        print('Done')
