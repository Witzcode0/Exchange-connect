"""empty message

Revision ID: 22f3a3d55609
Revises: 398cd5e31ec7
Create Date: 2021-11-12 17:13:18.972409

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '22f3a3d55609'
down_revision = '398cd5e31ec7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_announcement', 'result_date')
    op.drop_column('corporate_announcement', 'concall_date')
    op.add_column('result_tracker_group_companies', sa.Column('concall_date', sa.DateTime(), nullable=True))
    op.add_column('result_tracker_group_companies', sa.Column('concall_url', sa.String(length=256), nullable=True))
    op.add_column('result_tracker_group_companies', sa.Column('result_date', sa.DateTime(), nullable=True))
    op.drop_constraint('result_tracker_cannouncement_id_fkey', 'result_tracker_group_companies', type_='foreignkey')
    op.drop_column('result_tracker_group_companies', 'announcement_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('result_tracker_group_companies', sa.Column('announcement_id', sa.BIGINT(), autoincrement=False, nullable=False))
    op.create_foreign_key('result_tracker_cannouncement_id_fkey', 'result_tracker_group_companies', 'corporate_announcement', ['announcement_id'], ['id'], ondelete='CASCADE')
    op.drop_column('result_tracker_group_companies', 'result_date')
    op.drop_column('result_tracker_group_companies', 'concall_url')
    op.drop_column('result_tracker_group_companies', 'concall_date')
    op.add_column('corporate_announcement', sa.Column('concall_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('corporate_announcement', sa.Column('result_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
