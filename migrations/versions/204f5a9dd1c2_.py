"""empty message

Revision ID: 204f5a9dd1c2
Revises: 93bee3837f7a
Create Date: 2019-04-04 13:16:13.610154

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '204f5a9dd1c2'
down_revision = '93bee3837f7a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('management_profile', sa.Column('profile_thumbnail', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('management_profile', 'profile_thumbnail')
    # ### end Alembic commands ###