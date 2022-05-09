"""
Schemas for "management profile" related models
"""

from flask import g
from marshmallow import pre_dump, fields, validates_schema, ValidationError

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.resources.account_profiles.models import AccountProfile
from app.resources.management_profiles.models import ManagementProfile


class ManagementProfileSchema(ma.ModelSchema):
    """
    Schema for loading "ManagementProfile" from request, and also
    formatting output
    """
    #sequence_id removed from default exclude because of the bulk user creation using xcel file
    #, 'sequence_id'
    class Meta:
        model = ManagementProfile
        include_fk = True
        dump_only = default_exclude + ('account_profile_id',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('api.managementprofileapi', row_id='<row_id>'),
        'collection': ma.URLFor('api.managementprofilelistapi')
    }, dump_only=True)

    profile_photo_url = ma.Url(dump_only=True)
    profile_thumbnail_url = ma.Url(dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of profile photo
        """
        call_load = False  # minor optimisation
        if any(phfield in self.fields.keys() for phfield in [
                'profile_photo_url', 'profile_photo',
                'profile_thumbnail_url', 'profile_thumbnail']):
            # call load urls only if the above fields are asked for
            call_load = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls()
        else:
            if call_load:
                objs.load_urls()


class AdminManagementProfileSchema(ManagementProfileSchema):
    """
    Schema for loading 'account_id' from request to pass
    account_id instead of account_profile_id in Post API
    """
    account_id = fields.Integer(dump_only=True)


class ManagementProfileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "management profiles" filters from request args
    """
    account_profile_id = fields.String(load_only=True)
    sort_by = fields.List(fields.String(), load_only=True, missing=[
        'sequence_id'])


class ManagementProfileOrderSchema(ma.Schema):
    """
    schema for loading "management profiles" from request
    """

    management_profile_ids = fields.List(fields.Integer(), required=True)
    account_profile_id = None

    def load_account_profile_id(self, data):
        """
        validate and fetch account_profile_id for
        management_profiles validation
        """
        ref_acc_id = g.current_user['account']['row_id']
        account_profile = AccountProfile.query.filter_by(
            account_id=ref_acc_id).first()
        if account_profile:
            self.account_profile_id = account_profile.row_id
        else:
            raise ValidationError(
                'Account id: %s does not exist'
                % str(ref_acc_id),
                'account_id')

        return self.account_profile_id

    @validates_schema(pass_original=True)
    def validate_management_profiles(self, data, original_data):
        """
        validate management profiles
        """
        error = False  # error flag
        ref_acc_profile_id = self.load_account_profile_id(data)
        fetched_ids = []
        missing = []  # row_ids for which management_profile doesn't exists

        # fetch the management_profiles for the given row_ids and account_id
        if ('management_profile_ids' in original_data and
                original_data['management_profile_ids']):
            row_ids = original_data['management_profile_ids']
            management_profiles = ManagementProfile.query.filter_by(
                account_profile_id=ref_acc_profile_id).filter(
                ManagementProfile.row_id.in_(row_ids)).all()

            # check if management_profile for all given row_ids exists or not
            if management_profiles:
                for management_profile in management_profiles:
                    fetched_ids.append(management_profile.row_id)
            missing = set(row_ids) - set(fetched_ids)

        if missing:
            error = True

        if error:
            raise ValidationError(
                'Either management profiles: %s do not exist or does not '
                'have same account_profile_id' % missing,
                'management profiles')


class AdminManagementProfileOrderSchema(ManagementProfileOrderSchema):
    """
    Schema for loading management profiles from admin PUT API
    """

    account_id = fields.Integer(required=True)

    def load_account_profile_id(self, data):
        """
        validate account_id and fetch account_profile_id for
        management_profiles validation
        """
        # check account_profile exist or not then assign
        # provided account_id to the account_profile_id of table
        if 'account_id' in data:
            ref_acc_profile = AccountProfile.query.filter_by(
                account_id=data['account_id']).first()
            if ref_acc_profile:
                self.account_profile_id = ref_acc_profile.row_id
            else:
                raise ValidationError(
                    'Account id: %s does not exist'
                    % str(data['account_id']),
                    'account_id')

        return self.account_profile_id
