"""empty message

Revision ID: 27c4708b7d78
Revises: 240c89202342
Create Date: 2018-03-26 16:06:54.305941

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27c4708b7d78'
down_revision = '240c89202342'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('webinar', 'open_to_all')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('webinar', sa.Column('open_to_all', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.execute("UPDATE webinar SET open_to_all=true")
    # ### end Alembic commands ###
