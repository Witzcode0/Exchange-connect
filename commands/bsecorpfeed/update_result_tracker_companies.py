import datetime
import re

from flask_script import Command, Option

from app import db
from app.resources.bse.models import BSEFeed
from app.resources.results.models import AccountResultTracker
from app.resources.results.helpers import get_concall_date, extract_pdf_by_url


class UpdateResultComp(Command):
    """
    Command to update ec category from bse corp feed

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

    def run(self, verbose, dry):
        if verbose:
            print('---' + str(datetime.datetime.utcnow()) + '---')
            print('updating corporate announcement date...')

        start = '2021-09-01'
        end = '2021-12-24'

        bsefeeds = BSEFeed.query.filter(BSEFeed.dt_tm.between(start, end)).order_by(BSEFeed.dt_tm.asc())

        for each_feed in bsefeeds:
            if each_feed.descriptor_id == 80 and each_feed.acc_id:
                if 'Investor Meet - Intimation' in each_feed.news_sub:
                    try:
                        date = get_concall_date(True, each_feed.attachment_url)
                        if date:
                            acc = AccountResultTracker.query. \
                                filter(AccountResultTracker.account_id == each_feed.acc_id).first()
                            if acc:
                                AccountResultTracker.query.filter(
                                    AccountResultTracker.account_id == each_feed.acc_id).update({
                                    AccountResultTracker.concall_date: date,
                                    AccountResultTracker.concall_bse_id: each_feed.row_id},
                                    synchronize_session=False)
                            else:
                                db.session.add(AccountResultTracker(
                                    account_id=each_feed.acc_id,
                                    concall_date=date,
                                    concall_bse_id=each_feed.row_id
                                ))
                            db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        print(e)

            result_keyword = 'financial results'
            cleaner = re.compile('<.*?>')
            result_keywords = ['audited financial result', 'un-audited financial results',
                               'unaudited financial results', 'audited financial results',
                               'unaudited financial statements', 'audited financial results', 'quarter ended',
                               'quarterly results', 'quarterly result', 'quarter ended', 'half year ended', 'half year',
                               'nine month ended', '9 month ended', 'financial year ended', 'financial year',
                               'audited results', 'audited result', 'unaudited results', 'un-audited result',
                               'un-audited results', 'standalone and consolidated audited financial results',
                               'standalone and consolidated audited financial result',
                               'standalone and consolidated un-audited financial results',
                               'standalone and consolidated unaudited financial results',
                               'standalone & consolidated audited financial results',
                               'standalone & consolidated audited financial result',
                               'standalone & consolidated unaudited financial results',
                               'standalone & consolidated un-audited financial results', 'standalone & consolidated',
                               'standalone and consolidated', 'result', 'results', 'performance',
                               'september quarter results', 'september quarter result', 'june quarter results',
                               'june quarter result', 'march quarter results', 'march quarter result',
                               'december quarter results', 'december quarter result', 'quarter and half year ended',
                               'quarter and nine months ended', 'quarter and nine month ended',
                               'quarter and full year ended.']
            if each_feed.descriptor_id == 9 and each_feed.acc_id:
                if each_feed.type_of_meeting and each_feed.descriptor == 'Board Meeting':
                    temp = re.sub(cleaner, '', each_feed.news_body.lower())
                    newsbody = re.sub(r'\s+', ' ', temp)
                    if any(x in newsbody for x in result_keywords):
                    # if result_keyword in each_feed.news_body.lower():
                        print(each_feed.date_of_meeting)

                        if each_feed.date_of_meeting != '':
                            try:
                                acc = AccountResultTracker.query. \
                                    filter(AccountResultTracker.account_id == each_feed.acc_id).first()
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
                                        AccountResultTracker.account_id == each_feed.acc_id).update({
                                            AccountResultTracker.result_intimation_id: each_feed.row_id,
                                            AccountResultTracker.result_declaration_id: result_url_id},
                                        synchronize_session=False)
                                else:
                                    db.session.add(AccountResultTracker(
                                        account_id=each_feed.acc_id,
                                        result_intimation_id=each_feed.row_id
                                    ))
                                db.session.commit()
                            except Exception as e:
                                db.session.rollback()
                                print(e)
                    else:
                        text = extract_pdf_by_url(each_feed.attachment_url)
                        kk = [''.join(x.split()) for x in result_keywords]
                        if any(keyword in text.lower() for keyword in kk):
                            if each_feed.date_of_meeting != '':
                                try:
                                    acc = AccountResultTracker.query. \
                                        filter(AccountResultTracker.account_id == each_feed.acc_id).first()
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
                                            AccountResultTracker.account_id == each_feed.acc_id).update({
                                            AccountResultTracker.result_intimation_id: each_feed.row_id,
                                            AccountResultTracker.result_declaration_id: result_url_id},
                                            synchronize_session=False)
                                    else:
                                        db.session.add(AccountResultTracker(
                                            account_id=each_feed.acc_id,
                                            result_intimation_id=each_feed.row_id
                                        ))
                                    db.session.commit()
                                except Exception as e:
                                    db.session.rollback()
                                    print(e)
                elif each_feed.type_of_meeting == 'Board Meeting' and each_feed.descriptor == 'Dividend':
                    temp = re.sub(cleaner, '', each_feed.news_body.lower())
                    newsbody = re.sub(r'\s+', ' ', temp)
                    if any(x in newsbody for x in result_keywords):
                    # if result_keyword in each_feed.news_body.lower():
                        print(each_feed.date_of_meeting)

                        if each_feed.date_of_meeting != '':
                            try:
                                acc = AccountResultTracker.query. \
                                    filter(AccountResultTracker.account_id == each_feed.acc_id).first()
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
                                        AccountResultTracker.account_id == each_feed.acc_id).update({
                                            AccountResultTracker.result_intimation_id: each_feed.row_id,
                                            AccountResultTracker.result_declaration_id: result_url_id},
                                        synchronize_session=False)
                                else:
                                    db.session.add(AccountResultTracker(
                                        account_id=each_feed.acc_id,
                                        result_intimation_id=each_feed.row_id
                                    ))
                                db.session.commit()
                            except Exception as e:
                                db.session.rollback()
                                print(e)
                    else:
                        text = extract_pdf_by_url(each_feed.attachment_url)
                        kk = [''.join(x.split()) for x in result_keywords]
                        if any(keyword in text.lower() for keyword in kk):
                            if each_feed.date_of_meeting != '':
                                try:
                                    acc = AccountResultTracker.query. \
                                        filter(AccountResultTracker.account_id == each_feed.acc_id).first()
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
                                            AccountResultTracker.account_id == each_feed.acc_id).update({
                                            AccountResultTracker.result_intimation_id: each_feed.row_id,
                                            AccountResultTracker.result_declaration_id: result_url_id},
                                            synchronize_session=False)
                                    else:
                                        db.session.add(AccountResultTracker(
                                            account_id=each_feed.acc_id,
                                            result_intimation_id=each_feed.row_id
                                        ))
                                    db.session.commit()
                                except Exception as e:
                                    db.session.rollback()
                                    print(e)
            if (each_feed.descriptor_id == 30 or each_feed.descriptor_id == 186) and each_feed.acc_id:
                if each_feed.type_of_announce == 'Intimation' or \
                        each_feed.type_of_announce == "Delay in Financial Results" or \
                        each_feed.type_of_announce == "Regulation 23(9)- Disclosure of Related Party Transactions on consolidated basis":
                    continue
                elif each_feed.descriptor == "Investor Presentation":
                    continue
                elif 'delay in submission' in each_feed.news_body.lower():
                    continue
                else:
                    try:
                        acc = AccountResultTracker.query. \
                            filter(AccountResultTracker.account_id == each_feed.acc_id).first()
                        if acc:
                            AccountResultTracker.query.filter(
                                AccountResultTracker.account_id == each_feed.acc_id).update({
                                AccountResultTracker.result_declaration_id: each_feed.row_id},
                                synchronize_session=False)
                        else:
                            db.session.add(AccountResultTracker(
                                account_id=each_feed.acc_id,
                                result_declaration_id=each_feed.row_id
                            ))
                        db.session.commit()
                    except Exception as e:
                        db.session.rollback()
                        print(e)
