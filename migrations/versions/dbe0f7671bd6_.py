"""empty message

Revision ID: dbe0f7671bd6
Revises: 32ac501c1d61
Create Date: 2021-10-08 17:06:09.689140

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'dbe0f7671bd6'
down_revision = '5b479528a506'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('descriptor_master', sa.Column('cat_id', sa.Integer(), nullable=True))
    op.drop_constraint('descriptor_master_category_id_fkey', 'descriptor_master', type_='foreignkey')
    op.create_foreign_key('descriptor_corporate_category_fkey', 'descriptor_master', 'corporate_announcement_category', ['cat_id'], ['id'])
    op.drop_column('descriptor_master', 'category_id')
    op.add_column('bse_corp_feed', sa.Column('acc_id', sa.Integer(), nullable=True))
    op.add_column('bse_corp_feed', sa.Column('deleted', sa.Boolean(), nullable=True))
    op.drop_constraint('bse_corp_feed_account_id_fkey', 'bse_corp_feed', type_='foreignkey')
    op.create_foreign_key('bse_corp_feed_acc_id_fkey', 'bse_corp_feed', 'account', ['acc_id'], ['id'])
    op.drop_column('bse_corp_feed', 'account_id')
    op.add_column('descriptor_master', sa.Column('deleted', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('descriptor_master', sa.Column('category_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint('descriptor_corporate_category_fkey', 'descriptor_master', type_='foreignkey')
    op.create_foreign_key('descriptor_master_category_id_fkey', 'descriptor_master', 'corporate_announcement_category', ['category_id'], ['id'])
    op.drop_column('descriptor_master', 'cat_id')
    op.drop_column('descriptor_master', 'deleted')
    op.add_column('bse_corp_feed', sa.Column('account_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint('bse_corp_feed_acc_id_fkey', 'bse_corp_feed', type_='foreignkey')
    op.create_foreign_key('bse_corp_feed_account_id_fkey', 'bse_corp_feed', 'account', ['account_id'], ['id'])
    op.drop_column('bse_corp_feed', 'deleted')
    op.drop_column('bse_corp_feed', 'acc_id')
    # ### end Alembic commands ###
