"""empty message

Revision ID: e3fc21c53e56
Revises: ec00a90a9592
Create Date: 2018-02-21 13:41:47.403128

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3fc21c53e56'
down_revision = 'ec00a90a9592'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('account_profile', 'account_id', type_=sa.BigInteger())
    op.alter_column('archive_file', 'created_by', type_=sa.BigInteger())
    op.alter_column('archive_file', 'updated_by', type_=sa.BigInteger())
    op.alter_column('archive_file', 'account_id', type_=sa.BigInteger())
    op.alter_column('c_follow', 'sent_by', type_=sa.BigInteger())
    op.alter_column('c_follow', 'company_id', type_=sa.BigInteger())
    op.alter_column('company', 'updated_by', type_=sa.BigInteger())
    op.alter_column('company', 'created_by', type_=sa.BigInteger())
    op.alter_column('contact', 'sent_by', type_=sa.BigInteger())
    op.alter_column('contact', 'sent_to', type_=sa.BigInteger())
    op.alter_column('contact_request', 'sent_to', type_=sa.BigInteger())
    op.alter_column('contact_request', 'sent_by', type_=sa.BigInteger())
    op.alter_column('corporate_announcement', 'audio_file_id', type_=sa.BigInteger())
    op.alter_column('corporate_announcement', 'video_file_id', type_=sa.BigInteger())
    op.alter_column('corporate_announcement', 'account_id', type_=sa.BigInteger())
    op.alter_column('corporate_announcement', 'transcript_file_id', type_=sa.BigInteger())
    op.alter_column('corporate_announcement', 'created_by', type_=sa.BigInteger())
    op.alter_column('corporate_announcement', 'updated_by', type_=sa.BigInteger())
    op.alter_column('designation', 'updated_by', type_=sa.BigInteger())
    op.alter_column('designation', 'created_by', type_=sa.BigInteger())
    op.alter_column('event', 'created_by', type_=sa.BigInteger())
    op.alter_column('event', 'event_type_id', type_=sa.BigInteger())
    op.alter_column('event', 'account_id', type_=sa.BigInteger())
    op.alter_column('event', 'updated_by', type_=sa.BigInteger())
    op.alter_column('event_bookmark', 'event_id', type_=sa.BigInteger())
    op.alter_column('event_bookmark', 'created_by', type_=sa.BigInteger())
    op.alter_column('event_bookmark', 'account_id', type_=sa.BigInteger())
    op.alter_column('event_invite', 'user_id', type_=sa.BigInteger())
    op.alter_column('event_invite', 'created_by', type_=sa.BigInteger())
    op.alter_column('event_invite', 'updated_by', type_=sa.BigInteger())
    op.alter_column('event_library_file', 'created_by', type_=sa.BigInteger())
    op.alter_column('event_library_file', 'updated_by', type_=sa.BigInteger())
    op.alter_column('event_library_file', 'account_id', type_=sa.BigInteger())
    op.alter_column('event_type', 'updated_by', type_=sa.BigInteger())
    op.alter_column('event_type', 'account_id', type_=sa.BigInteger())
    op.alter_column('event_type', 'created_by', type_=sa.BigInteger())
    op.alter_column('feed_item', 'post_id', type_=sa.BigInteger())
    op.alter_column('feed_item', 'user_id', type_=sa.BigInteger())
    op.alter_column('feed_item', 'corporate_announcement_id', type_=sa.BigInteger())
    op.alter_column('industry', 'created_by', type_=sa.BigInteger())
    op.alter_column('industry', 'updated_by', type_=sa.BigInteger())
    op.alter_column('industry', 'sector_id', type_=sa.BigInteger())
    op.alter_column('management_profile', 'account_profile_id', type_=sa.BigInteger())
    op.alter_column('news_item_archive', 'news_id', type_=sa.BigInteger())
    op.alter_column('news_item_archive', 'updated_by', type_=sa.BigInteger())
    op.alter_column('news_item_archive', 'created_by', type_=sa.BigInteger())
    op.alter_column('news_item_archive', 'account_id', type_=sa.BigInteger())
    op.alter_column('notification', 'account_id', type_=sa.BigInteger())
    op.alter_column('notification', 'user_id', type_=sa.BigInteger())
    op.alter_column('post', 'updated_by', type_=sa.BigInteger())
    op.alter_column('post', 'post_shared_id', type_=sa.BigInteger())
    op.alter_column('post', 'account_id', type_=sa.BigInteger())
    op.alter_column('post', 'created_by', type_=sa.BigInteger())
    op.alter_column('post_comment', 'account_id', type_=sa.BigInteger())
    op.alter_column('post_comment', 'post_id', type_=sa.BigInteger())
    op.alter_column('post_comment', 'updated_by', type_=sa.BigInteger())
    op.alter_column('post_comment', 'in_reply_to', type_=sa.BigInteger())
    op.alter_column('post_comment', 'created_by', type_=sa.BigInteger())
    op.alter_column('post_library_file', 'created_by', type_=sa.BigInteger())
    op.alter_column('post_library_file', 'updated_by', type_=sa.BigInteger())
    op.alter_column('post_library_file', 'account_id', type_=sa.BigInteger())
    op.alter_column('post_star', 'created_by', type_=sa.BigInteger())
    op.alter_column('post_star', 'post_id', type_=sa.BigInteger())
    op.alter_column('post_star', 'updated_by', type_=sa.BigInteger())
    op.alter_column('post_star', 'account_id', type_=sa.BigInteger())
    op.alter_column('sector', 'updated_by', type_=sa.BigInteger())
    op.alter_column('sector', 'created_by', type_=sa.BigInteger())
    op.alter_column('survey', 'account_id', type_=sa.BigInteger())
    op.alter_column('survey', 'updated_by', type_=sa.BigInteger())
    op.alter_column('survey', 'created_by', type_=sa.BigInteger())
    op.alter_column('user', 'role_id', type_=sa.BigInteger())
    op.alter_column('user', 'account_id', type_=sa.BigInteger())
    op.alter_column('user_profile', 'user_id', type_=sa.BigInteger())
    op.alter_column('user_profile', 'account_id', type_=sa.BigInteger())


def downgrade():
    pass
