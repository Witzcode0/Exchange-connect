"""empty message

Revision ID: dff90b7b2963
Revises: 22f3a3d55609
Create Date: 2021-11-12 18:35:05.385151

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dff90b7b2963'
down_revision = '22f3a3d55609'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('result_tracker_user_id_group_name_uniquekey', 'result_tracker_group', type_='unique')
    op.create_unique_constraint('result_tracker_user_id_group_name_uniquekey', 'result_tracker_group', ['user_id', 'group_name'])
    op.drop_column('result_tracker_group', 'deleted')
    op.create_unique_constraint('result_tracker_group_id_account_id_user_id_uniquekey', 'result_tracker_group_companies', ['group_id', 'account_id', 'user_id'])
    op.drop_constraint('result_tracker_group_id_account_id_deleted_user_id_uniquekey', 'result_tracker_group_companies', type_='unique')
    op.drop_column('result_tracker_group_companies', 'deleted')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('result_tracker_group_companies', sa.Column('deleted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.create_unique_constraint('result_tracker_group_id_account_id_deleted_user_id_uniquekey', 'result_tracker_group_companies', ['group_id', 'account_id', 'deleted', 'user_id'])
    op.drop_constraint('result_tracker_group_id_account_id_user_id_uniquekey', 'result_tracker_group_companies', type_='unique')
    op.add_column('result_tracker_group', sa.Column('deleted', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_constraint('result_tracker_user_id_group_name_uniquekey', 'result_tracker_group', type_='unique')
    op.create_unique_constraint('result_tracker_user_id_group_name_uniquekey', 'result_tracker_group', ['user_id', 'group_name', 'deleted'])
    # ### end Alembic commands ###
