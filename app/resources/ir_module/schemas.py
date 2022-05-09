"""
Schemas for "follows" related models
"""

from marshmallow import fields, validate, validates_schema, ValidationError
from marshmallow import (
    fields, validate, pre_dump, ValidationError, validates_schema)

from app import ma, g
from app.base.schemas import default_exclude, BaseReadArgsSchema, user_fields
from app.resources.ir_module.models import IrModule,IrModuleHeading
from flask import request, current_app, g
from app.common.utils import get_s3_download_link, do_nothing

class IrModuleSchema(ma.ModelSchema):
    """
    Schema for formatting ir module
    """
    _default_exclude_fields = []

    class Meta:
        model = IrModule
        include_fk = True
        dump_only = default_exclude 

    favourite = ma.Boolean(dump_only=True)

    headings = ma.List(ma.Nested(
        'app.resources.ir_module.schemas.IrModuleHeadingSchema',
        dump_only=True))
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema',  only=user_fields,
        dump_only=True)

    @pre_dump(pass_many=True)
    def loads_urls(self, objs, many):
        """
        Loads the urls of profile photo, cover photo,
        profile thumbnail and cover thumbnail
        """
        call_load = False  # minor optimisation
        thumbnail_only = False  # default thumbnail
        if any(phfield in self.fields.keys() for phfield in [
            'profile_photo_url', 'infoghraphic',
                'profile_thumbnail_url', 'profile_thumbnail']):
            # call load urls only if the above fields are asked for
            call_load = True
            if all(phfield not in self.fields.keys() for phfield in [
                    'profile_photo_url', 'infoghraphic']):
                thumbnail_only = True

        if many:  # #TODO: write optimized load_url here instead?
            for obj in objs:
                if call_load:
                    obj.load_urls(thumbnail_only=thumbnail_only)
        else:
            if call_load:
                objs.load_urls(thumbnail_only=thumbnail_only)

    @pre_dump(pass_many=True)
    def loads_favourite(self, objs, many):
        """
        load favourite for individual user
        """
        if many:
            for obj in objs:
                obj.load_favourite()
        else:
            objs.load_favourite()


class IrModuleReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for read args
    """
    # sort_by = fields.List(fields.String(), load_only=True, missing=['favourite'])
    sort = fields.String(validate=validate.OneOf(['asc', 'dsc']),
                         missing='dsc')
    module_name = fields.String(load_only=True)
    favourite = fields.Boolean(load_only=True)

class IrModuleHeadingSchema(ma.ModelSchema):
    """
    Schema for formatting ir module heading
    """
    _default_exclude_fields = []

    class Meta:
        model = IrModuleHeading
        include_fk = True
        dump_only = default_exclude

    # ir_module = ma.Nested(
    #     'app.resources.ir_module.schemas.IrModuleSchema',
    #     dump_only=True)
    creator = ma.Nested(
        'app.resources.users.schemas.UserSchema',  only=user_fields,
        dump_only=True)



class IrModuleHeadingReadArgsSchema(BaseReadArgsSchema):
    """
    Schema for read args
    """
    ir_module_id = fields.String(load_only=True)
    deactivated = fields.Boolean(load_only=True)
