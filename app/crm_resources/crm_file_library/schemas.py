"""
Schemas for "crm file library" related models
"""

from flask import g
from marshmallow import pre_dump, fields, validates_schema, ValidationError
from sqlalchemy import and_, or_

from app import ma
from app.base.schemas import default_exclude, BaseReadArgsSchema
from app.crm_resources.crm_file_library.models import CRMLibraryFile
from app.crm_resources.crm_contacts.models import CRMContact
from app.resources.contacts.models import Contact


class CRMLibraryFileSchema(ma.ModelSchema):
    """
    Schema for loading "CRMLibraryFile" from request, and also
    formatting output
    """

    class Meta:
        model = CRMLibraryFile
        include_fk = True
        load_only = ('deleted', 'account_id', 'updated_by', 'created_by')
        dump_only = default_exclude + ('account_id', 'updated_by', 'deleted',
                                       'created_by',)

    # extra fields for output
    links = ma.Hyperlinks({
        'self': ma.URLFor('crm_api.crmlibraryfileapi', row_id='<row_id>'),
        'collection': ma.URLFor('crm_api.crmlibraryfilelistapi')
    }, dump_only=True)

    file_url = ma.Url(dump_only=True)
    thumbnail_url = ma.Url(dump_only=True)

    @validates_schema(pass_original=True)
    def validate_user_id_exist_as_contact(self, data, original_data):
        """
        Validation for user_id, user_id exists in crm contact or
        connection(Contact) for current_user
        """
        error = False
        if 'user_id' in original_data and original_data['user_id']:
            if not CRMContact.query.filter(and_(
                    CRMContact.user_id == original_data['user_id'],
                    CRMContact.created_by == g.current_user['row_id'])
                    ).first():
                if not Contact.query.filter(or_(and_(
                        Contact.sent_to == original_data['user_id'],
                        Contact.sent_by == g.current_user['row_id']),
                        and_(Contact.sent_to == g.current_user['row_id'],
                             Contact.sent_by == original_data['user_id']))
                        ).first():
                    error = True

        if error:
            raise ValidationError(
                '%s id is not contact or connection' % original_data[
                    'user_id'], 'user_id')

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of filename and thumbnail_name
        """
        call_load = False  # minor optimisation
        thumbnail_only = False  # default thumbnail
        if any(phfield in self.fields.keys() for phfield in [
                'file_url', 'filename',
                'thumbnail_url', 'thumbnail_name']):
            # call load urls only if the above fields are asked for
            call_load = True
            if all(phfield not in self.fields.keys() for phfield in [
                    'file_url', 'filename']):
                thumbnail_only = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls(thumbnail_only=thumbnail_only)
        else:
            if call_load:
                objs.load_urls(thumbnail_only=thumbnail_only)


class CRMLibraryFileReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for reading "crm library file" filters from request args
    """
    user_id = fields.Integer(load_only=True)
