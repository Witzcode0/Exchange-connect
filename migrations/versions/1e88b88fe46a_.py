"""empty message

Revision ID: 1e88b88fe46a
Revises: 38e7eee80c94
Create Date: 2018-12-12 15:10:07.983562

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1e88b88fe46a'
down_revision = '38e7eee80c94'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event', sa.Column('open_to_all', sa.Boolean(), nullable=True))
    op.execute('update corporate_access_event set open_to_all=False')
    op.add_column('corporate_access_event_invitee', sa.Column('uninvited', sa.Boolean(), nullable=True))
    op.execute('update corporate_access_event_invitee set uninvited=False')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_event', 'open_to_all')
    op.drop_column('corporate_access_event_invitee', 'uninvited')
    # ### end Alembic commands ###
