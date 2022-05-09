"""empty message

Revision ID: 7027c00174ba
Revises: 6b674a1ef38a
Create Date: 2021-11-11 19:51:13.861730

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7027c00174ba'
down_revision = '6b674a1ef38a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('result_tracker_group_companies', sa.Column('user_id', sa.BigInteger(), nullable=True))
    op.create_unique_constraint('result_tracker_group_id_account_id_deleted_uniquekey', 'result_tracker_group_companies', ['group_id', 'account_id', 'deleted'])
    op.drop_constraint('result_tracker_group_id_account_id_uniquekey', 'result_tracker_group_companies', type_='unique')
    op.create_foreign_key('result_tracker_group_company_user_fkey', 'result_tracker_group_companies', 'user', ['user_id'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('result_tracker_group_company_user_fkey', 'result_tracker_group_companies', type_='foreignkey')
    op.create_unique_constraint('result_tracker_group_id_account_id_uniquekey', 'result_tracker_group_companies', ['group_id', 'account_id', 'deleted'])
    op.drop_constraint('result_tracker_group_id_account_id_deleted_uniquekey', 'result_tracker_group_companies', type_='unique')
    op.drop_column('result_tracker_group_companies', 'user_id')
    # ### end Alembic commands ###
