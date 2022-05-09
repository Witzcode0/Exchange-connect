"""empty message

Revision ID: a0e1ebaddd7e
Revises: 97113148f8c7
Create Date: 2018-02-19 17:09:58.541318

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app


# revision identifiers, used by Alembic.
revision = 'a0e1ebaddd7e'
down_revision = '97113148f8c7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('identifier', sa.String(length=128), nullable=True))
    op.add_column('account', sa.Column('isin_number', sa.String(length=128), nullable=True))
    op.add_column('account', sa.Column('sedol', sa.String(length=128), nullable=True))
    op.add_column('account_profile', sa.Column('cover_thumbnail', sa.String(), nullable=True))
    op.add_column('account_profile', sa.Column('profile_thumbnail', sa.String(), nullable=True))
    op.drop_column('account_profile', 'management_profile')
    op.add_column('archive_file', sa.Column('thumbnail_name', sa.String(), nullable=True))
    op.add_column('designation', sa.Column('account_type', app.base.model_fields.ChoiceString(app.resources.accounts.constants.ACCT_TYPES_CHOICES)))
    op.add_column('designation', sa.Column('designation_level', app.base.model_fields.ChoiceString(app.resources.designations.constants.DES_LEVEL_TYPES_CHOICES)))
    op.execute("UPDATE designation SET account_type='" + app.resources.accounts.constants.ACCT_CORPORATE + "'")
    op.alter_column('designation', 'account_type', nullable=False)
    op.execute("UPDATE designation SET designation_level='" + app.resources.designations.constants.DES_LEVEL_BOD + "'")
    op.alter_column('designation', 'designation_level', nullable=False)
    op.add_column('event', sa.Column('account_id', sa.Integer(), nullable=False))
    op.add_column('event', sa.Column('attended_participated', sa.BigInteger(), nullable=True))
    op.add_column('event', sa.Column('avg_rating', sa.Numeric(precision=5, scale=2), nullable=True))
    op.add_column('event', sa.Column('contact_email', app.base.model_fields.LCString(length=128), nullable=True))
    op.add_column('event', sa.Column('contact_number', sa.String(length=32), nullable=True))
    op.add_column('event', sa.Column('contact_person', sa.String(length=256), nullable=True))
    op.add_column('event', sa.Column('dial_in_details', sa.String(length=1024), nullable=True))
    op.add_column('event', sa.Column('event_type_id', sa.Integer(), nullable=False))
    op.add_column('event', sa.Column('host', sa.String(length=256), nullable=True))
    op.add_column('event', sa.Column('language', app.base.model_fields.ChoiceString(app.resources.events.constants.EVENT_LANGUAGE_CHOICES), nullable=True))
    op.add_column('event', sa.Column('maybe_participated', sa.BigInteger(), nullable=True))
    op.add_column('event', sa.Column('not_participated', sa.BigInteger(), nullable=True))
    op.add_column('event', sa.Column('open_to_all', sa.Boolean(), nullable=True))
    op.add_column('event', sa.Column('participated', sa.BigInteger(), nullable=True))
    op.add_column('event', sa.Column('public_event', sa.Boolean(), nullable=True))
    op.add_column('event', sa.Column('speaker', sa.String(length=256), nullable=True))
    op.add_column('event', sa.Column('timezone', app.base.model_fields.ChoiceString(app.resources.users.constants.ALL_TIMEZONES_CHOICES), nullable=True))
    op.create_foreign_key(None, 'event', 'account', ['account_id'], ['id'])
    op.create_foreign_key(None, 'event', 'event_type', ['event_type_id'], ['id'])
    op.drop_column('event', 'event_type')
    op.drop_constraint('news_item_archive_guid_key', 'news_item_archive', type_='unique')
    op.add_column('post_library_file', sa.Column('thumbnail_name', sa.String(), nullable=True))
    op.add_column('survey', sa.Column('ended_at', sa.DateTime(), nullable=True))
    op.add_column('survey', sa.Column('started_at', sa.DateTime(), nullable=True))
    op.add_column('survey', sa.Column('success_message', sa.String(length=512), nullable=True))
    op.add_column('survey', sa.Column('welcome_message', sa.String(length=512), nullable=True))
    op.add_column('user', sa.Column('deactivated', sa.Boolean(), nullable=True))
    op.add_column('user', sa.Column('search_privacy', sa.ARRAY(app.base.model_fields.ChoiceString(app.resources.accounts.constants.ACCT_TYPES_CHOICES)), nullable=True))
    op.add_column('user', sa.Column('token_valid_mobile', sa.Boolean(), nullable=True))
    op.add_column('user_profile', sa.Column('cover_thumbnail', sa.String(), nullable=True))
    op.add_column('user_profile', sa.Column('profile_thumbnail', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_profile', 'profile_thumbnail')
    op.drop_column('user_profile', 'cover_thumbnail')
    op.drop_column('user', 'token_valid_mobile')
    op.drop_column('user', 'search_privacy')
    op.drop_column('user', 'deactivated')
    op.drop_column('survey', 'welcome_message')
    op.drop_column('survey', 'success_message')
    op.drop_column('survey', 'started_at')
    op.drop_column('survey', 'ended_at')
    op.drop_column('post_library_file', 'thumbnail_name')
    op.create_unique_constraint('news_item_archive_guid_key', 'news_item_archive', ['guid'])
    op.add_column('event', sa.Column('event_type', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'event', type_='foreignkey')
    op.drop_constraint(None, 'event', type_='foreignkey')
    op.drop_column('event', 'timezone')
    op.drop_column('event', 'speaker')
    op.drop_column('event', 'public_event')
    op.drop_column('event', 'participated')
    op.drop_column('event', 'open_to_all')
    op.drop_column('event', 'not_participated')
    op.drop_column('event', 'maybe_participated')
    op.drop_column('event', 'language')
    op.drop_column('event', 'host')
    op.drop_column('event', 'event_type_id')
    op.drop_column('event', 'dial_in_details')
    op.drop_column('event', 'contact_person')
    op.drop_column('event', 'contact_number')
    op.drop_column('event', 'contact_email')
    op.drop_column('event', 'avg_rating')
    op.drop_column('event', 'attended_participated')
    op.drop_column('event', 'account_id')
    op.drop_column('designation', 'designation_level')
    op.drop_column('designation', 'account_type')
    op.drop_column('archive_file', 'thumbnail_name')
    op.add_column('account_profile', sa.Column('management_profile', postgresql.ARRAY(postgresql.JSONB(astext_type=sa.Text())), autoincrement=False, nullable=True))
    op.drop_column('account_profile', 'profile_thumbnail')
    op.drop_column('account_profile', 'cover_thumbnail')
    op.drop_column('account', 'sedol')
    op.drop_column('account', 'isin_number')
    op.drop_column('account', 'identifier')
    # ### end Alembic commands ###
