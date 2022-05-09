"""empty message

Revision ID: 8721d0a85680
Revises: 9dbeb508c2e2
Create Date: 2019-09-20 11:47:58.274651

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8721d0a85680'
down_revision = '9dbeb508c2e2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('account', sa.Column('facebook_id', sa.String(length=512), nullable=True))
    op.add_column('account', sa.Column('linkedin_id', sa.String(length=512), nullable=True))
    op.add_column('account', sa.Column('twitter_id', sa.String(length=512), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('account', 'twitter_id')
    op.drop_column('account', 'linkedin_id')
    op.drop_column('account', 'facebook_id')
    # ### end Alembic commands ###
