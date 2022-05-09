"""
Schemas for "crm group" related models
"""

from marshmallow import (
    fields, validate, pre_dump, ValidationError, validates_schema, post_dump)
from flask import g
from marshmallow_sqlalchemy import field_for
from sqlalchemy import and_, or_
from sqlalchemy.orm import load_only, joinedload

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.crm_resources.crm_groups.models import CRMGroup
from app.crm_resources.crm_contacts.models import CRMContact
from app.resources.contacts.models import Contact
from app.resources.users.models import User

final_user_fields = user_fields + ['email', 'crm_contact_grouped']
contact_user = ['sendee.' + fld for fld in final_user_fields]
contact_user += ['sender.' + fld for fld in final_user_fields]
contact_user += ['sent_to', 'sent_by']


class CRMGroupSchema(ma.ModelSchema):
    """
    Schema for loading "crm group" from request, and also formatting output
    """

    _cached_contact = None
    contact_ids = fields.List(fields.Integer(), dump_only=True)

    class Meta:
        model = CRMGroup
        include_fk = True
        load_only = ('created_by', 'account_id',)
        dump_only = default_exclude + ('created_by', 'account_id')
        exclude = ('group_j', )

    group_contacts = ma.List(ma.Nested(
        'app.resources.users.schemas.UserSchema', only=final_user_fields),
        dump_only=True)
    group_crm_contacts = ma.List(ma.Nested(
        'app.crm_resources.crm_contacts.schemas.CRMContactSchema',
        exclude=['user', 'crmgrouped'], dump_only=True))
    group_crm_connections = ma.List(ma.Nested(
        'app.resources.contacts.schemas.ContactSchema', only=contact_user),
        dump_only=True)

    group_icon_url = ma.Url(dump_only=True)

    @pre_dump(pass_many= True)
    def loads_urls(self, objs, many):
        if not many:
            objs.load_urls()

    @post_dump(pass_many=True)
    def loads_crm_group_connections(self, objs, many):
        """
        Loads crm group connections
        """
        if many:
            for obj in objs:
                if 'group_crm_connections' in obj and \
                        obj['group_crm_connections'] :
                    group_crm_connections = []
                    for each in obj['group_crm_connections']:
                        the_other = each['sender']
                        if each['sent_by'] == g.current_user['row_id']:
                            the_other = each['sendee']
                        # if (the_other['account']['account_type'] !=
                        #         g.current_user['account_type']):
                        # #ToDo: only contacts from other a/c types displayed?
                        group_crm_connections.append(the_other)
                    obj['group_crm_connections'] = group_crm_connections

        else:
            if 'group_crm_connections' in objs and objs['group_crm_connections']:
                group_crm_connections = []
                for each in objs['group_crm_connections']:
                    the_other = each['sender']
                    if each['sent_by'] == g.current_user['row_id']:
                        the_other = each['sendee']
                    # if (the_other['account']['account_type'] !=
                    #         g.current_user['account_type']):
                    # #ToDo: only contacts from other a/c types displayed?
                    group_crm_connections.append(the_other)
                objs['group_crm_connections'] = group_crm_connections

    @validates_schema(pass_original=True)
    def validate_contact_ids_exists(self, data, original_data):
        """
        Validate contact ids exists in crm contact or connection(Contact) for
        current user
        """

        error = False
        self._cached_contact = []
        cids = []
        missing = []
        if 'contact_ids' in original_data and original_data['contact_ids']:
            cids = original_data['contact_ids'][:]

        # validate user_ids, and load all the _cached_contact
        if cids:
            iids = []
            for iid in cids:
                try:
                    iids.append(int(iid))
                except Exception as e:
                    continue

            query = CRMContact.query.filter(and_(
                CRMContact.user_id.in_(iids),
                CRMContact.created_by == g.current_user['row_id']))
            crm_contact_ids = []
            for c in query.all():
                self._cached_contact.append(c.user)
                crm_contact_ids.append(c.user.row_id)

            connect_missing = set(iids) - set(crm_contact_ids)

            if connect_missing:
                query = Contact.query.filter(or_(
                    and_(Contact.sent_by.in_(
                        connect_missing), Contact.sent_to ==
                         g.current_user['row_id']),
                    and_(Contact.sent_to.in_(
                        connect_missing), Contact.sent_by ==
                         g.current_user['row_id']))).options(
                    # sendee and related stuff
                    joinedload(Contact.sendee).load_only('row_id').joinedload(
                        User.profile),
                    # sender and related stuff
                    joinedload(Contact.sender).load_only('row_id').joinedload(
                        User.profile))

                contact_ids = []  # for validating missing (incorrect user ids)
                for c in query.all():
                    the_contact = c.sender if c.sent_to == \
                                  g.current_user['row_id'] else c.sendee
                    self._cached_contact.append(the_contact)
                    contact_ids.append(the_contact.row_id)

                missing = set(connect_missing) - set(contact_ids)
                if missing:
                    error = True

        if error:
            raise ValidationError(
                'Contacts: %s do not exist' % missing,
                'contact_ids'
            )


class CRMGroupReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "CRM group" filters from request args
    """

    name = fields.String(load_only=True)


class BulkGroupSchema(ma.Schema):
    """
    Schema for bulk group
    """
    row_id = fields.Integer()
    group_name = fields.String()
    contact_ids = fields.List(fields.Integer())


class BulkGroupContactSchema(ma.Schema):
    """
    Schema for contact excel import
    """
    excel_contacts = ma.List(ma.Nested(
        "app.crm_resources.crm_contacts.schemas.CRMContactSchema"),
        load_only=True)
    group = ma.Nested(BulkGroupSchema, load_only=True)
