"""empty message

Revision ID: 894c503fb959
Revises: c53a4b249820
Create Date: 2018-09-11 16:36:54.556965

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '894c503fb959'
down_revision = 'c53a4b249820'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('c_acc_profile_id_user_id_key', 'management_profile', ['account_profile_id', 'user_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('c_acc_profile_id_user_id_key', 'management_profile', type_='unique')
    # ### end Alembic commands ###