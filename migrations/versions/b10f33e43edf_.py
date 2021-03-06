"""empty message

Revision ID: b10f33e43edf
Revises: 028f63946ffb
Create Date: 2021-11-23 12:27:08.813813

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b10f33e43edf'
down_revision = '3836b0ddda42'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('result_master',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('created_date', sa.DateTime(), nullable=True),
    sa.Column('modified_date', sa.DateTime(), nullable=True),
    sa.Column('account_id', sa.BigInteger(), nullable=False),
    sa.Column('result_date', sa.DateTime(), nullable=True),
    sa.Column('result_url', sa.String(length=256), nullable=True),
    sa.Column('concall_date', sa.DateTime(), nullable=True),
    sa.Column('announcement_id', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], name='result_master_account_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['announcement_id'], ['bse_corp_feed.id'], name='result_master_bse_id_fkey', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('result_master')
    # ### end Alembic commands ###
