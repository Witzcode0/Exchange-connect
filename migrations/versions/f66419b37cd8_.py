"""empty message

Revision ID: f66419b37cd8
Revises: 184a77948ed0
Create Date: 2018-05-09 15:37:50.059458

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f66419b37cd8'
down_revision = '184a77948ed0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'enable_chat')
    op.drop_column('user', 'search_privacy')
    op.drop_column('user', 'timezone')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('timezone', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('search_privacy', postgresql.ARRAY(sa.VARCHAR()), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('enable_chat', sa.BOOLEAN(), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
