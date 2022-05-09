"""empty message

Revision ID: 9e6cb1f5b288
Revises: 52eab9b76f85
Create Date: 2018-03-08 18:13:49.324007

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9e6cb1f5b288'
down_revision = '52eab9b76f85'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('feed_item', 'post_id', existing_type=sa.BIGINT(), nullable=False)
    op.drop_constraint('feed_item_corporate_announcement_fkey', 'feed_item', type_='foreignkey')
    op.drop_constraint('c_check_post_corporate_announcement_not_all_null_key', 'feed_item', type_='check')
    op.drop_column('feed_item', 'corporate_announcement_id')
    op.drop_constraint('notification_corporate_announcement_id_fkey', 'notification', type_='foreignkey')
    op.drop_column('notification', 'corporate_announcement_id')
    op.drop_constraint('post_corporate_id_fkey', 'post', type_='foreignkey')
    op.drop_column('post', 'corporate_id')
    op.drop_table('corporate_announcement')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('corporate_announcement',
    sa.Column('id', sa.BIGINT(), nullable=False),
    sa.Column('created_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('modified_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('account_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('created_by', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('updated_by', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('announcement_date', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('category', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('sub_category', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('subject', sa.VARCHAR(length=512), autoincrement=False, nullable=True),
    sa.Column('description', sa.VARCHAR(length=2048), autoincrement=False, nullable=True),
    sa.Column('transcript_file_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('audio_file_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('video_file_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('deleted', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.CheckConstraint('(transcript_file_id IS NOT NULL) OR (audio_file_id IS NOT NULL) OR (video_file_id IS NOT NULL)', name='c_check_transcript_audio_video_not_all_null_key'),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], name='corporate_announcement_account_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['audio_file_id'], ['archive_file.id'], name='corporate_announcement_audio_file_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], name='corporate_announcement_created_by_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['transcript_file_id'], ['archive_file.id'], name='corporate_announcement_transcript_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['updated_by'], ['user.id'], name='corporate_announcement_updated_by_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['video_file_id'], ['archive_file.id'], name='corporate_announcement_video_file_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name='corporate_announcement_pkey')
    )
    op.add_column('post', sa.Column('corporate_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('post_corporate_id_fkey', 'post', 'corporate_announcement', ['corporate_id'], ['id'], ondelete='CASCADE')
    op.add_column('notification', sa.Column('corporate_announcement_id', sa.BIGINT(), autoincrement=False, nullable=True))
    op.create_foreign_key('notification_corporate_announcement_id_fkey', 'notification', 'corporate_announcement', ['corporate_announcement_id'], ['id'], ondelete='CASCADE')
    op.add_column('feed_item', sa.Column('corporate_announcement_id', sa.BIGINT(), autoincrement=False, nullable=True))
    op.create_foreign_key('feed_item_corporate_announcement_fkey', 'feed_item', 'corporate_announcement', ['corporate_announcement_id'], ['id'], ondelete='CASCADE')
    op.alter_column('feed_item', 'post_id', existing_type=sa.BIGINT(), nullable=True)
    op.create_check_constraint('c_check_post_corporate_announcement_not_all_null_key', 'feed_item', '((post_id IS NOT NULL) OR '
                               '(corporate_announcement_id IS NOT NULL))')
    # ### end Alembic commands ###