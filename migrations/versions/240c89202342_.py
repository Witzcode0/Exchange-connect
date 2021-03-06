"""empty message

Revision ID: 240c89202342
Revises: 1d9b4ec155f7
Create Date: 2018-03-24 14:48:30.109472

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '240c89202342'
down_revision = '1d9b4ec155f7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('registration_request', sa.Column('other_selected', sa.Boolean(), nullable=True))
    op.execute("UPDATE registration_request SET other_selected=false")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('registration_request', 'other_selected')
    # ### end Alembic commands ###
