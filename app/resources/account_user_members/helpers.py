"""
Helper classes/functions for "account user member" package.
"""

from flask import g
from sqlalchemy.orm import load_only
from sqlalchemy import and_

from app import db
from app.resources.accounts.models import Account
from app.resources.account_user_members.models import AccountUserMember
from app.resources.users.models import User


def add_user_member_for_child_accounts(
        user_id, group_account_id, is_admin):
    """
    Add user member for child accounts of user's group account
    :param user_id: user_id of group account id
    :param group_account_id: account id which is group type
    :return:
    """
    child_account_ids = []
    if group_account_id:
        child_account_ids = [a.row_id for a in Account.query.filter(
            Account.parent_account_id == group_account_id).options(
            load_only('row_id')).all()]

    if user_id and child_account_ids:
        try:
            for ch_id in child_account_ids:
                account_member = AccountUserMember(
                    account_id=ch_id, member_id=user_id,
                    member_is_admin=is_admin,
                    created_by=g.current_user['row_id'],
                    updated_by=g.current_user['row_id'])
                db.session.add(account_member)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
    return


def update_user_member_for_child_account(
        account_id, old_child_account_ids, child_account_ids):
    """
    When update child account for particular group account, so update user
    member also change according to child accounts
    :param account_id: group account id
    :param old_child_account_ids: old child account ids
    :param child_account_ids: new child account ids
    :return:
    """
    try:
        users = User.query.filter(
                User.account_id == account_id).options(
                load_only('row_id', 'is_admin', 'account_id')).all()
        user_ids = [a.row_id for a in users]
        # if new child accounts exists for another group member so delete all
        if child_account_ids:
            AccountUserMember.query.filter(and_(
                AccountUserMember.account_id.in_(child_account_ids),
                AccountUserMember.member_id.notin_(user_ids))
            ).delete(synchronize_session=False)
            db.session.commit()

        for user in users:
            # if old_child_account then remove from account user member
            if old_child_account_ids:
                AccountUserMember.query.filter(and_(
                    AccountUserMember.member_id == user.row_id,
                    AccountUserMember.account_id.in_(
                        old_child_account_ids))).delete(
                    synchronize_session=False)
                db.session.commit()
            # new child account user member
            if child_account_ids:
                for child_account in child_account_ids:
                    db.session.add(AccountUserMember(
                        account_id=child_account,
                        member_id=user.row_id,
                        member_is_admin=user.is_admin,
                        created_by=g.current_user['row_id'],
                        updated_by=g.current_user['row_id']))
                    db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
    return
