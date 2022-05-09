"""
Models for "ir-module" package.
"""
import os

from sqlalchemy import UniqueConstraint
from flask import request, current_app, g
from app.common.utils import get_s3_download_link, do_nothing

from app import db
from app.base.models import BaseModel
from app.resources.account_profiles.models import AccountProfile
from app.resources.users.models import User


# association table for user favourite ir module

class favirmodule(BaseModel):
    """
    create favirmodule
    """

    __tablename__ = 'favirmodule'

    ir_module_id = db.Column(db.BigInteger, db.ForeignKey(
        'ir_module.id', name='fav_ir_module_id_fkey', ondelete="CASCADE"),
    nullable=False)
    user_id = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='fav_ir_module_user_id_fkey', ondelete="CASCADE"),
    nullable=False)

    __table_args__ = (
        UniqueConstraint('ir_module_id', 'user_id', name='fav_ir_module_user_id_key'),
    )

    def __init__(self,ir_module_id=None,user_id=None, *args, **kwargs):
        self.ir_module_id = ir_module_id
        self.user_id = user_id
        super(favirmodule, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<favirmodule %s>' % (self.row_id)

class IrModule(BaseModel):
    """
    create IRModule
    """

    __tablename__ = 'ir_module'

    root_profile_photo_folder_key = 'IR_MODULE_PHOTO_FOLDER'

    module_name = db.Column(db.String(512), nullable=False)
    infoghraphic = db.Column(db.String(9216))
    profile_thumbnail = db.Column(db.String())
    infoghraphic_url = db.Column(db.String())
    profile_thumbnail_url = db.Column(db.String())

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ir_module_created_by_fkey'))
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ir_module_updated_by_fkey'))
    deactivated = db.Column(db.Boolean, default=False)

    headings = db.relationship('IrModuleHeading', backref=db.backref(
        'irmodule_headings'))
    creator = db.relationship('User', backref=db.backref(
        'ir_module_creator', lazy='dynamic'),
    foreign_keys='IrModule.created_by')

    favourite = None


    def __init__(self, *args, **kwargs):
        super(IrModule, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<IrModule %s>' % (self.row_id)

    def load_urls(self, with_redirect=False, expires_in=3600,
                  thumbnail_only=False):
        """
        Populates the profile_photo_url, profile_thumbnail_url
        dynamic properties
        """
        s3_url = ''
        thumbnail_bucket_name = ''
        if not self.infoghraphic and not self.profile_thumbnail:
            return
        sub_folder = self.file_subfolder_name()
        if current_app.config['S3_UPLOAD']:
            if self.profile_thumbnail:
                thumbnail_bucket_name = current_app.config[
                    'S3_THUMBNAIL_BUCKET']
                s3_url = 'https://s3-ap-southeast-1.amazonaws.com/'
            signer = get_s3_download_link
        else:
            signer = do_nothing
        if self.profile_thumbnail:
            self.profile_thumbnail_url = os.path.join(
                s3_url, thumbnail_bucket_name,
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.profile_thumbnail)
        if self.infoghraphic:
            self.infoghraphic_url = signer(os.path.join(
                current_app.config[self.root_profile_photo_folder_key],
                sub_folder, self.infoghraphic), expires_in=expires_in)
        # if thumbnail_only:
        #     return
        return

    def load_favourite(self):
        """
        favourite load 
        """
        fav = favirmodule.query.filter_by(
            ir_module_id=self.row_id,
            user_id = g.current_user['row_id']).first()
        if fav:
            self.favourite = True
        else:
            self.favourite = False


class IrModuleHeading(BaseModel):
    """
    create Ir module headings
    """

    __tablename__ = 'ir_module_heading'

    heading = db.Column(db.String(512), nullable=False)
    description = db.Column(db.String())
    ir_module_id = db.Column(db.BigInteger, db.ForeignKey(
        'ir_module.id', name='ir_module_heading_ir_module_fkey'))
    deactivated = db.Column(db.Boolean, default=False)

    created_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ir_module_heading_created_by_fkey'))
    updated_by = db.Column(db.BigInteger, db.ForeignKey(
        'user.id', name='ir_module_heading_updated_by_fkey'))

    creator = db.relationship('User', backref=db.backref(
        'ir_module_heading_creator', lazy='dynamic'),
    foreign_keys='IrModuleHeading.created_by')
    # ir_module = db.relationship('IrModule', backref=db.backref(
    #     'ir_module_heading_ir_module', lazy='dynamic'),
    # foreign_keys='IrModuleHeading.ir_module_id')

    def __init__(self, *args, **kwargs):
        super(IrModuleHeading, self).__init__(*args, **kwargs)

    def __repr__(self):
        return '<IrModuleHeading %s>' % (self.row_id)
