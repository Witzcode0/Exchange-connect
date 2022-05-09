"""empty message

Revision ID: 519eda76c617
Revises: cd02c97a1a8e
Create Date: 2018-09-29 12:33:29.801186

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '519eda76c617'
down_revision = 'cd02c97a1a8e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('webinar_host', sa.Column('conference_url', sa.String(length=256), nullable=True))
    op.add_column('webinar_participant', sa.Column('conference_url', sa.String(length=256), nullable=True))
    op.add_column('webinar_rsvp', sa.Column('conference_url', sa.String(length=256), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('webinar_rsvp', 'conference_url')
    op.drop_column('webinar_participant', 'conference_url')
    op.drop_column('webinar_host', 'conference_url')
    # ### end Alembic commands ###
