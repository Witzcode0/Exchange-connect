"""empty message

Revision ID: 2aba3e13bb04
Revises: 894c503fb959
Create Date: 2018-09-12 16:38:30.703806

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2aba3e13bb04'
down_revision = '894c503fb959'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('c_acc_profile_id_sequence_id_key', 'management_profile', type_='unique')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('c_acc_profile_id_sequence_id_key', 'management_profile', ['account_profile_id', 'sequence_id'])
    # ### end Alembic commands ###