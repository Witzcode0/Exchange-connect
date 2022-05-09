"""
Common functionalities for schemas, can include classes, functions.
"""

from marshmallow import fields, validate
from webargs.flaskparser import use_args

from app import ma
from app.resources.accounts import constants as ACCT


default_exclude = ('created_date', 'modified_date', 'row_id', )

# user profile details
user_profile_fields = ['first_name', 'last_name', 'designation',
                       'profile_photo_url', 'profile_thumbnail_url']
# account fields
account_fields = ['row_id', 'account_name', 'account_type']
# user details that will be passed while populating user relation
user_fields = ['row_id', ]
user_fields += ['profile.' + fld for fld in user_profile_fields] + [
    'profile.links']
user_fields += ['account.' + fld for fld in account_fields]

# corporate access:
# event fields which will pass while populating event relation
ca_event_fields = ['row_id', 'title', 'event_type_id', 'event_sub_type_id',
                   'invite_logo_filename', 'invite_banner_filename',
                   'started_at', 'ended_at', 'collaborators', 'creator']
# webinar:
# webinar fields which will pass while populating webinar relation
webinar_fields = ['row_id', 'title', 'invite_logo_filename',
                  'invite_banner_filename', 'started_at', 'ended_at']
# webcast:
# webcast fields which will pass while populating webcast relation
webcast_fields = ['row_id', 'title', 'invite_logo_filename',
                  'invite_banner_filename', 'started_at', 'ended_at']

#e_meeting
#e_meeting fields which will pass while populating e_meeting relation
e_meeting_fields = ['row_id','meeting_subject','meeting_agenda','meeting_datetime']

# ca open meeting:
# ca open meeting fields which will pass while populating ca open
# meeting relation
ca_open_meeting_fields = ['row_id', 'title', 'event_type_id', 'creator',
                          'event_sub_type_id', 'started_at', 'ended_at']


def use_args_with(schema_cls, schema_kwargs=None, **kwargs):
    """
    Small helper to reduce boilerplate from: (unused)
    https://webargs.readthedocs.io/en/latest/advanced.html#reducing-boilerplate
    """
    schema_kwargs = schema_kwargs or {}

    def factory(request):
        strict = schema_kwargs.pop('strict', True)
        # Filter based on 'fields' query parameter
        only = request.args.get('pfields', schema_kwargs.pop('only', None))
        # Respect partial updates for PATCH requests
        partial = request.method == 'PATCH'
        # Add current request to the schema's context
        # and ensure we're always using strict mode
        return schema_cls(
            only=only, partial=partial, strict=strict,
            context={'request': request}, **schema_kwargs
        )
    return use_args(factory, **kwargs)


class BaseReadArgsSchema(ma.Schema):
    """
    A base schema for reading filters, pagination, sort from args using
    webargs.
    """
    page = fields.Integer(load_only=True, missing=1)
    per_page = fields.Integer(load_only=True, missing=10)
    sort_by = fields.List(fields.String(), load_only=True, missing=['row_id'])
    sort = fields.String(validate=validate.OneOf(['asc', 'dsc']),
                         missing='asc')
    # specific fields for return
    pfields = fields.List(fields.String(), load_only=True)
    # operator
    operator = fields.String(validate=validate.OneOf(['and', 'or']),
                             missing='and')
    # dates
    created_date_from = fields.DateTime(load_only=True)
    created_date_to = fields.DateTime(load_only=True)
    apply_domain_filter = fields.Boolean(load_only=True, missing=True)

    _db_exclude_fields = [
        'page', 'per_page', 'sort_by', 'sort', 'pfields', 'operator',
        'created_date_from', 'created_date_to', ]


class BaseCommonSchema(ma.Schema):
    """
    Schema for Common of every api
    """
    launch = fields.Boolean(load_only=True)
    order = fields.Boolean(load_only=True)
    token = fields.String(load_only=True)
