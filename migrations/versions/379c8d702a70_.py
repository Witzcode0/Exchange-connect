"""empty message

Revision ID: 379c8d702a70
Revises: 56c7cbd8ea34
Create Date: 2019-04-25 12:58:47.036758

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '379c8d702a70'
down_revision = '56c7cbd8ea34'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('newsaccounts',
    sa.Column('news_id', sa.BigInteger(), nullable=False),
    sa.Column('account_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['account_id'], ['account.id'], name='newsaccounts_account_id_fkey', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['news_id'], ['news_item.id'], name='newsaccounts_news_id_fkey', ondelete='CASCADE'),
    sa.UniqueConstraint('news_id', 'account_id', name='ac_news_id_account_id_key')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('newsaccounts')
    # ### end Alembic commands ###