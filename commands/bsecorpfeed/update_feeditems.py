import re
import datetime
import json
import subprocess
import dateutil
import requests
from dateutil import parser
from flask import current_app

from sqlalchemy import and_
from sqlalchemy.orm import load_only

from flask_script import Command, Option

from app import db
from app.resources.accounts.models import Account
from app.resources.accounts import constants as ACC
from app.common.helpers import time_converter
from app.resources.bse.models import BSEFeed
from app.resources.descriptor.models import BSE_Descriptor
from app.resources.bse.schemas import BseCorpSchema
from app.resources.corporate_announcements_category.models import CorporateAnnouncementCategory
from app.resources.corporate_announcements.models import CorporateAnnouncement
from queueapp.bse_announcements.notification_tasks import add_bse_announcement_notification
from app.resources.notifications import constants as NOTIFY
from commands.bsecorpfeed.email_tasks import send_bse_new_descriptor_added_email
from app.resources.result_tracker_companies.models import ResultTrackerGroupCompanies
from app.resources.results.models import AccountResultTracker
from app.resources.results.schemas import AccountResultTrackerSchema
from app.resources.results.helpers import get_concall_date
from app.resources.bse_mf_etf.schemas import BseMfEtfSchema
from app.resources.results.helpers import extract_pdf_by_url


class FetchBseFeed(Command):
    """
        Command to fetch news, and populate the newsfeed db

        :arg verbose:        print progress
        :arg dry:
            dry run
        """

    option_list = [
        Option('--verbose', '-v', dest='verbose', action='store_true',
               default=False),
        Option('--dry', '-dry', dest='dry', action='store_true',
               default=False),
    ]

    def remove_reps(self, status, feeds, dist_attachments):
        # status 'AD' and 'CND'
        distinct_data = []
        for each in feeds:
            if status == 'AD':
                if dist_attachments and (each['AttachmentName'], each['Descriptor']) in dist_attachments:
                    distinct_data.append(each)
                    dist_attachments.remove((each['AttachmentName'], each['Descriptor']))
            elif status == 'CND':
                if dist_attachments and (each['CompanyName'], each['NewsBody'], each['Descriptor']) in dist_attachments:
                    distinct_data.append(each)
                    dist_attachments.remove((each['CompanyName'], each['NewsBody'], each['Descriptor']))
        return distinct_data

    def search(self, myDict, lookup):
        for key, value in myDict.items():
            if isinstance(value, list):
                for v in value:
                    v = v.replace('_', ' ')
                    if lookup in v:
                        return key
                    elif v in lookup:
                        return key

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('extracting bse corp feed ...')

        categories = db.session.query(CorporateAnnouncementCategory).all()
        cat_df = {}
        category = "news"
        cate_id = 10
        acc_id = None
        for cat in categories:
            cat_df[cat.name] = cat.bse_keywords

        accounts = db.session.query(Account).filter(and_(
            Account.deleted.is_(False),
            Account.account_type != ACC.ACCT_ADMIN,
            Account.domain_id == 1)).options(
            load_only('row_id', 'account_name', 'identifier')).order_by(
            Account.account_name).all()

        descriptor_ids = db.session.query(BSE_Descriptor).all()
        descriptor_df = {}
        for each in descriptor_ids:
            descriptor_df[each.descriptor_id] = each.row_id

        descriptor_ids = db.session.query(BSE_Descriptor).all()
        descriptor_cat_df = {}
        for each in descriptor_ids:
            descriptor_cat_df[each.descriptor_id] = each.cat_id

        account_dict = {}
        account_instances = {}
        for account in accounts:
            if account.identifier:
                identifier = account.identifier.split('-')[0]
                account_dict[identifier] = account.row_id
                account_instances[identifier] = account

        feeds = ""
        h = "00"
        m = "00"
        s = "00"
        date_today = datetime.datetime.utcnow()
        day_today = date_today.day
        try:
            first_row = db.session.query(BSEFeed.dt_tm).first()
        except Exception as e:
            print(e)
            return
        if first_row is not None:
            try:
                last_updated_date = db.session.query(BSEFeed.dt_tm).order_by(BSEFeed.dt_tm.desc()).first()
            except Exception as e:
                print(e)
                return

            if last_updated_date:
                for each in last_updated_date:
                    if each == (None,):
                        h = "00"
                        m = "00"
                        s = "00"
                    elif each.day == day_today:
                        dttm = time_converter(each, 'Asia/Kolkata', 'UTC')
                        print("dttm :", dttm)
                        de = dttm  # each[0]
                        hh = de.hour
                        h = str(hh)
                        mm = de.minute
                        m = str(mm)
                        ss = de.second + 1
                        s = str(ss)
                    else:
                        h = "00"
                        m = "00"
                        s = "00"

        args = ['curl', '-X', 'POST', '-d',
                '{"Username":uname, "Password":pwd, "Hr":hrs, "Min":min, "Sec": sec}'.replace('hrs', '"{}"'.format(
                    str(h))).replace('min', '"{}"'.format(str(m))).replace('sec', '"{}"'.format(str(s))).replace(
                    'uname', '"{}"'.format(current_app.config['BSE_UNAME'])).replace('pwd', '"{}"'.format(current_app.config['BSE_PASSWORD'])), '-H', 'Content-Type: application/json',
                current_app.config['BSE_FEED_URL']]

        process = subprocess.Popen(args, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        try:
            simple_obj = stdout.decode()
            feeds = json.loads(simple_obj)
        except UnicodeEncodeError:
            try:
                simple_obj = stdout.decode()
                encoded_obj = simple_obj.encode('ascii', 'ignore')
                re_simple_obj = encoded_obj.decode()
                feeds = json.loads(re_simple_obj)
            except Exception as e:
                print(e)
                return

        try:
            if isinstance(feeds, list):
                cnt = 0
                # attachment name and descriptor
                revised = []
                # null values in attachment
                n_revised = []

                for each in feeds:
                    if each['AttachmentName'] != '':
                        revised.append((each['AttachmentName'], each['Descriptor']))
                    else:
                        n_revised.append((each['CompanyName'], each['NewsBody'], each['Descriptor']))

                # attachment_list = [(d['CompanyName'], d['AttachmentName'], d['Descriptor']) for d in feeds]
                rdist_feeds = []
                ndist_feeds = []
                if revised:
                    dist_revised = list(set(revised))
                    rdist_feeds = self.remove_reps(status='AD', feeds=feeds, dist_attachments=dist_revised)
                if n_revised:
                    dist_n_revised = list(set(n_revised))
                    ndist_feeds = self.remove_reps(status='CND', feeds=feeds, dist_attachments=dist_n_revised)
                # dist_attachment = list(set(attachment_list))
                dist_feeds = rdist_feeds + ndist_feeds

                # Add data to list which are not in descriptor_master table
                descriptor_ids_notin_db = []
                add_to_descriptor = []
                for each_feed in dist_feeds:
                    if int(each_feed['DescriptorID']) not in descriptor_df.keys():
                        if int(each_feed['DescriptorID']) not in descriptor_ids_notin_db:
                            descriptor_ids_notin_db.append(int(each_feed['DescriptorID']))
                            add_to_descriptor.append((int(each_feed['DescriptorID']), each_feed['Descriptor']))

                # Add list to database
                if add_to_descriptor:
                    for each_descriptor in add_to_descriptor:
                        descriptor = BSE_Descriptor(descriptor_id=each_descriptor[0],
                                                    descriptor_name=each_descriptor[1])
                        db.session.add(descriptor)
                    db.session.commit()
                    # Sends an email if new descriptor has been added
                    # send_bse_new_descriptor_added_email(True, add_to_descriptor)

                for res in dist_feeds:
                    cnt += 1
                    bse_feed = {}
                    mf_feed = {}
                    try:
                        json_obj = json.loads(json.dumps(res))
                    except Exception as e:
                        print(e)
                        continue

                    if cat_df and json_obj:
                        if json_obj['Descriptor'] or json_obj['HeadLine']:
                            key_descriptor = self.search(cat_df, json_obj['Descriptor'])
                            key_head_line = self.search(cat_df, json_obj['HeadLine'])
                            if key_descriptor is not None:
                                category = key_descriptor
                            elif key_head_line is not None:
                                category = key_head_line
                            else:
                                category = "news"
                    if json_obj['SCRIP_CD'] in account_dict:
                        acc_id = account_dict[json_obj['SCRIP_CD']]
                        if int(json_obj['DescriptorID']) in descriptor_cat_df:
                            cate_id = descriptor_cat_df.get(int(json_obj['DescriptorID']))
                    else:
                        acc_id = None
                        if int(json_obj['DescriptorID']) in descriptor_cat_df:
                            cate_id = descriptor_cat_df.get(int(json_obj['DescriptorID']))

                        MT_ETF_DESCRIPTORS = ['18', '199', '200']
                        if any(x in json_obj['DescriptorID'] for x in MT_ETF_DESCRIPTORS):
                            mf_feed['scrip_cd'] = json_obj['SCRIP_CD']
                            mf_feed['company_name'] = json_obj['CompanyName']
                            mf_feed['file_status'] = json_obj['Filestatus']
                            mf_feed['head_line'] = json_obj['HeadLine']
                            mf_feed['news_sub'] = json_obj['NewsSub']
                            mf_feed['attachment_name'] = json_obj['AttachmentName']
                            mf_feed['news_body'] = json_obj['NewsBody']
                            mf_feed['descriptor'] = json_obj['Descriptor']
                            mf_feed['critical_news'] = json_obj['CriticalNews']
                            mf_feed['type_of_announce'] = json_obj['TypeofAnnounce']
                            mf_feed['type_of_meeting'] = json_obj['TypeofMeeting']
                            mf_feed['descriptor_id'] = json_obj['DescriptorID']
                            mf_feed['attachment_url'] = json_obj['ATTACHMENTURL']

                            mf_feed_dt_tm = time_converter(dateutil.parser.parse(json_obj['DT_TM']), 'UTC',
                                                           'Asia/Kolkata')
                            # bse_feed_dt_tm = time_converter(dateutil.parser.parse(
                            #     json_obj['DT_TM']), 'Asia/Calcutta', 'UTC')
                            # bse_feed_dt_t = bse_feed_dt_tm.strftime("%Y-%m-%dT%H:%M:%SZ")

                            data, errors = BseMfEtfSchema().load(mf_feed)
                            if errors:
                                print(errors)
                                continue
                            data.dt_tm = mf_feed_dt_tm
                            if json_obj['DateofMeeting'] != '':
                                mf_feed_date_of_meeting = dateutil.parser.parse(json_obj['DateofMeeting'])
                                data.date_of_meeting = mf_feed_date_of_meeting
                            db.session.add(data)
                            db.session.commit()
                            continue

                    bse_feed['scrip_cd'] = json_obj['SCRIP_CD']
                    bse_feed['company_name'] = json_obj['CompanyName']
                    bse_feed['file_status'] = json_obj['Filestatus']
                    bse_feed['head_line'] = json_obj['HeadLine']
                    bse_feed['news_sub'] = json_obj['NewsSub']
                    bse_feed['attachment_name'] = json_obj['AttachmentName']
                    bse_feed['news_body'] = json_obj['NewsBody']
                    bse_feed['descriptor'] = json_obj['Descriptor']
                    bse_feed['critical_news'] = json_obj['CriticalNews']
                    bse_feed['type_of_announce'] = json_obj['TypeofAnnounce']
                    bse_feed['type_of_meeting'] = json_obj['TypeofMeeting']
                    bse_feed['descriptor_id'] = json_obj['DescriptorID']
                    bse_feed['attachment_url'] = json_obj['ATTACHMENTURL']
                    bse_feed['exchange_category'] = category
                    bse_feed['acc_id'] = acc_id
                    bse_feed['ec_category'] = cate_id
                    bse_feed['source'] = 'bse_api'

                    bse_feed_dt_tm = time_converter(dateutil.parser.parse(json_obj['DT_TM']), 'UTC', 'Asia/Kolkata')
                    tdate = time_converter(dateutil.parser.parse(json_obj['Tradedate']), 'UTC', 'Asia/Kolkata')
                    # bse_feed_dt_tm = time_converter(dateutil.parser.parse(
                    #     json_obj['DT_TM']), 'Asia/Calcutta', 'UTC')
                    # bse_feed_dt_t = bse_feed_dt_tm.strftime("%Y-%m-%dT%H:%M:%SZ")

                    data, errors = BseCorpSchema().load(bse_feed)
                    if errors:
                        print(errors)
                        continue
                    data.dt_tm = bse_feed_dt_tm
                    data.trade_date = tdate
                    if json_obj['DateofMeeting'] != '':
                        bse_feed_date_of_meeting = dateutil.parser.parse(json_obj['DateofMeeting'])
                        data.date_of_meeting = bse_feed_date_of_meeting
                    db.session.add(data)
                    db.session.commit()

                    if bse_feed['acc_id'] != None:
                        add_bse_announcement_notification.s(True, data.row_id, NOTIFY.NT_BSE_CORP_ANNOUNCEMENT).delay()
                    print('counter of records {}'.format(cnt))

                    if json_obj['SCRIP_CD'] in account_dict:
                        acnt = account_dict[json_obj['SCRIP_CD']]
                        if int(json_obj['DescriptorID']) in descriptor_df:
                            bse_desc = descriptor_df[int(json_obj['DescriptorID'])]
                        else:
                            bse_desc = None

                        bse_announcement_date = time_converter(dateutil.parser.parse(json_obj['DT_TM']), 'UTC',
                                                               'Asia/Kolkata')
                        # bse_announcement_dt = bse_announcement_date.strftime("%Y-%m-%dT%H:%M:%SZ")

                        try:
                            if acnt and bse_desc:
                                db.session.add(CorporateAnnouncement(
                                    category=category,
                                    subject=json_obj['NewsSub'],
                                    description=json_obj['NewsBody'],
                                    url=json_obj['ATTACHMENTURL'],
                                    bse_type_of_announce=json_obj['TypeofAnnounce'],
                                    source='bse_api',
                                    account_id=acnt,
                                    bse_descriptor=bse_desc,
                                    announcement_date=bse_announcement_date,
                                    created_by=1,
                                    updated_by=1,
                                    category_id=cate_id
                                    ))
                                db.session.commit()
                        except Exception as e:
                            db.session.rollback()
                            print(e)

                        if int(json_obj['DescriptorID']) == 80 and acnt:
                            if 'Investor Meet - Intimation' in json_obj['NewsSub']:
                                try:
                                    date = get_concall_date(True, json_obj['ATTACHMENTURL'])
                                    if date:
                                        acc = AccountResultTracker.query.\
                                            filter(AccountResultTracker.account_id == acnt).first()
                                        if acc:
                                            AccountResultTracker.query.filter(
                                                AccountResultTracker.account_id == acnt).update({
                                                    AccountResultTracker.concall_date: date,
                                                    AccountResultTracker.concall_bse_id: data.row_id},
                                                synchronize_session=False)
                                        else:
                                            db.session.add(AccountResultTracker(
                                                account_id=acnt,
                                                concall_date=date,
                                                concall_bse_id=data.row_id
                                            ))
                                        db.session.commit()
                                except Exception as e:
                                    db.session.rollback()
                                    print(e)

                        result_keyword = 'financial results'
                        cleaner = re.compile('<.*?>')
                        result_keywords = ['audited financial result', 'un-audited financial results', 'unaudited financial results', 'audited financial results', 'unaudited financial statements', 'audited financial results', 'quarter ended', 'quarterly results', 'quarterly result', 'quarter ended', 'half year ended', 'half year', 'nine month ended', '9 month ended','financial year ended', 'financial year', 'audited results', 'audited result', 'unaudited results', 'un-audited result', 'un-audited results', 'standalone and consolidated audited financial results', 'standalone and consolidated audited financial result', 'standalone and consolidated un-audited financial results', 'standalone and consolidated unaudited financial results', 'standalone & consolidated audited financial results', 'standalone & consolidated audited financial result','standalone & consolidated unaudited financial results', 'standalone & consolidated un-audited financial results','standalone & consolidated', 'standalone and consolidated', 'result','results', 'performance', 'september quarter results','september quarter result', 'june quarter results', 'june quarter result','march quarter results', 'march quarter result', 'december quarter results','december quarter result', 'quarter and half year ended','quarter and nine months ended', 'quarter and nine month ended','quarter and full year ended.']
                        if int(json_obj['DescriptorID']) == 9 and acnt:
                            if json_obj['TypeofMeeting'] and json_obj['Descriptor'] == 'Board Meeting':
                                temp = re.sub(cleaner, '', json_obj['NewsBody'].lower())
                                newsbody = re.sub(r'\s+', ' ', temp)
                                if any(x in newsbody for x in result_keywords):
                                # if result_keyword in json_obj['NewsBody'].lower():
                                    if json_obj['DateofMeeting'] != '':
                                        bse_feed_date_of_meeting = time_converter(dateutil.parser.parse(
                                            json_obj['DateofMeeting']), 'UTC', 'Asia/Kolkata')

                                        try:
                                            acc = AccountResultTracker.query. \
                                                filter(AccountResultTracker.account_id == acnt).first()
                                            if acc:
                                                result_url_id = None
                                                result_date = None
                                                if acc.result_intimation_id:
                                                    result_date = db.session.query(BSEFeed.date_of_meeting). \
                                                        join(AccountResultTracker, BSEFeed.row_id ==
                                                             acc.result_intimation_id).first()[0]
                                                if acc.result_declaration_id:
                                                    if result_date:
                                                        result_url_date = db.session.query(BSEFeed.created_date). \
                                                            join(AccountResultTracker, BSEFeed.row_id ==
                                                                 acc.result_declaration_id).first()[0]
                                                        if result_date > result_url_date:
                                                            result_url_id = None
                                                        else:
                                                            result_url_id = acc.result_declaration_id
                                                    else:
                                                        result_url_id = acc.result_declaration_id
                                                AccountResultTracker.query.filter(
                                                    AccountResultTracker.account_id == acnt).update({
                                                    AccountResultTracker.result_intimation_id: data.row_id,
                                                    AccountResultTracker.result_declaration_id: result_url_id},
                                                    synchronize_session=False)
                                            else:
                                                db.session.add(AccountResultTracker(
                                                    account_id=acnt,
                                                    result_intimation_id=data.row_id
                                                ))
                                            db.session.commit()
                                        except Exception as e:
                                            db.session.rollback()
                                            print(e)
                                else:
                                    text = extract_pdf_by_url(json_obj['ATTACHMENTURL'])
                                    kk = [''.join(x.split()) for x in result_keywords]
                                    if any(keyword in text.lower() for keyword in kk):
                                        if json_obj['DateofMeeting'] != '':
                                            try:
                                                acc = AccountResultTracker.query. \
                                                    filter(AccountResultTracker.account_id == acnt).first()
                                                if acc:
                                                    result_url_id = None
                                                    result_date = None
                                                    if acc.result_intimation_id:
                                                        result_date = db.session.query(BSEFeed.date_of_meeting). \
                                                            join(AccountResultTracker, BSEFeed.row_id ==
                                                                 acc.result_intimation_id).first()[0]
                                                    if acc.result_declaration_id:
                                                        if result_date:
                                                            result_url_date = db.session.query(BSEFeed.created_date). \
                                                                join(AccountResultTracker, BSEFeed.row_id ==
                                                                     acc.result_declaration_id).first()[0]
                                                            if result_date > result_url_date:
                                                                result_url_id = None
                                                            else:
                                                                result_url_id = acc.result_declaration_id
                                                        else:
                                                            result_url_id = acc.result_declaration_id
                                                    AccountResultTracker.query.filter(
                                                        AccountResultTracker.account_id == acnt).update({
                                                        AccountResultTracker.result_intimation_id: data.row_id,
                                                        AccountResultTracker.result_declaration_id: result_url_id},
                                                        synchronize_session=False)
                                                else:
                                                    db.session.add(AccountResultTracker(
                                                        account_id=acnt,
                                                        result_intimation_id=data.row_id
                                                    ))
                                                db.session.commit()
                                            except Exception as e:
                                                db.session.rollback()
                                                print(e)
                            elif json_obj['TypeofMeeting'] == 'Board Meeting' and json_obj['Descriptor'] == 'Dividend':
                                temp = re.sub(cleaner, '', json_obj['NewsBody'].lower())
                                newsbody = re.sub(r'\s+', '', temp)
                                # newsbody = ' '.join(newsbody.strip())
                                if any(x in newsbody for x in result_keywords):
                                    # if result_keyword in newsbody:
                                    print(json_obj['DateofMeeting'])

                                    if json_obj['DateofMeeting'] != '':
                                        try:
                                            acc = AccountResultTracker.query. \
                                                filter(AccountResultTracker.account_id == acnt).first()
                                            if acc:
                                                result_url_id = None
                                                result_date = None
                                                if acc.result_intimation_id:
                                                    result_date = db.session.query(BSEFeed.date_of_meeting). \
                                                        join(AccountResultTracker, BSEFeed.row_id ==
                                                             acc.result_intimation_id).first()[0]
                                                if acc.result_declaration_id:
                                                    if result_date:
                                                        result_url_date = db.session.query(BSEFeed.created_date). \
                                                            join(AccountResultTracker, BSEFeed.row_id ==
                                                                 acc.result_declaration_id).first()[0]
                                                        if result_date > result_url_date:
                                                            result_url_id = None
                                                        else:
                                                            result_url_id = acc.result_declaration_id
                                                    else:
                                                        result_url_id = acc.result_declaration_id
                                                AccountResultTracker.query.filter(
                                                    AccountResultTracker.account_id == acnt).update({
                                                    AccountResultTracker.result_intimation_id: data.row_id,
                                                    AccountResultTracker.result_declaration_id: result_url_id},
                                                    synchronize_session=False)
                                            else:
                                                db.session.add(AccountResultTracker(
                                                    account_id=acnt,
                                                    result_intimation_id=data.row_id
                                                ))
                                            db.session.commit()
                                        except Exception as e:
                                            db.session.rollback()
                                            print(e)
                                else:
                                    text = extract_pdf_by_url(json_obj['ATTACHMENTURL'])
                                    kk = [''.join(x.split()) for x in result_keywords]
                                    if any(keyword in text.lower() for keyword in kk):
                                        if json_obj['DateofMeeting'] != '':
                                            try:
                                                acc = AccountResultTracker.query. \
                                                    filter(AccountResultTracker.account_id == acnt).first()
                                                if acc:
                                                    result_url_id = None
                                                    result_date = None
                                                    if acc.result_intimation_id:
                                                        result_date = db.session.query(BSEFeed.date_of_meeting). \
                                                            join(AccountResultTracker, BSEFeed.row_id ==
                                                                 acc.result_intimation_id).first()[0]
                                                    if acc.result_declaration_id:
                                                        if result_date:
                                                            result_url_date = db.session.query(BSEFeed.created_date). \
                                                                join(AccountResultTracker, BSEFeed.row_id ==
                                                                     acc.result_declaration_id).first()[0]
                                                            if result_date > result_url_date:
                                                                result_url_id = None
                                                            else:
                                                                result_url_id = acc.result_declaration_id
                                                        else:
                                                            result_url_id = acc.result_declaration_id
                                                    AccountResultTracker.query.filter(
                                                        AccountResultTracker.account_id == acnt).update({
                                                        AccountResultTracker.result_intimation_id: data.row_id,
                                                        AccountResultTracker.result_declaration_id: result_url_id},
                                                        synchronize_session=False)
                                                else:
                                                    db.session.add(AccountResultTracker(
                                                        account_id=acnt,
                                                        result_intimation_id=data.row_id
                                                    ))
                                                db.session.commit()
                                            except Exception as e:
                                                db.session.rollback()
                                                print(e)

                        if (int(json_obj['DescriptorID']) == 30 or int(json_obj['DescriptorID']) == 186) and acnt:
                            if json_obj['TypeofAnnounce'] == 'Intimation' or \
                                    json_obj['TypeofAnnounce'] == "Delay in Financial Results" or \
                                    json_obj['TypeofAnnounce'] == \
                                    "Regulation 23(9)- Disclosure of Related Party " \
                                    "Transactions on consolidated basis":
                                continue
                            elif json_obj['Descriptor'] == "Investor Presentation":
                                continue
                            elif 'delay in submission' in json_obj['NewsBody'].lower():
                                continue
                            else:
                                # update url in front of account_id in result tracker companies
                                try:
                                    acc = AccountResultTracker.query. \
                                        filter(AccountResultTracker.account_id == acnt).first()
                                    if acc:
                                        AccountResultTracker.query.filter(
                                            AccountResultTracker.account_id == acnt).update({
                                            AccountResultTracker.result_declaration_id: data.row_id},
                                            synchronize_session=False)
                                    else:
                                        db.session.add(AccountResultTracker(
                                            account_id=acnt,
                                            result_declaration_id=data.row_id
                                        ))
                                    db.session.commit()

                                except Exception as e:
                                    db.session.rollback()
                                    print(e)

                        # if account_instances[bse_feed['scrip_cd']]:
                        #     data.bsefeedaccount.append(account_instances[bse_feed['scrip_cd']])
                        #     db.session.add(data)
                        #     db.session.commit()
            elif isinstance(feeds, dict) and bool(feeds['Error_Msg']):
                print("No feed is available!")
                db.session.rollback()
            elif isinstance(feeds, dict) and bool(feeds['Authentication Failed']):
                print("Authentication Failed")
                db.session.rollback()
            elif isinstance(feeds, dict) and bool(feeds['Content mismatch']):
                print("Content mismatch")
                db.session.rollback()
        except UnicodeEncodeError:
            print("ascii codec can't encode character '\u2013' ")
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            print(e)

    print('---' + str(datetime.datetime.utcnow()) + '---')
    print('Done')
