"""empty message

Revision ID: fb20af7d37e4
Revises: cca507cc072b
Create Date: 2018-07-13 16:56:28.475711

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fb20af7d37e4'
down_revision = 'cca507cc072b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('webcast', sa.Column('presenter_url', sa.String(length=256), nullable=True))
    op.add_column('webinar', sa.Column('presenter_url', sa.String(length=256), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('webinar', 'presenter_url')
    op.drop_column('webcast', 'presenter_url')
    # ### end Alembic commands ###
