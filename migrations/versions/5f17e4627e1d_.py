"""empty message

Revision ID: 5f17e4627e1d
Revises: 8429068a8413
Create Date: 2018-03-29 20:55:05.704836

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f17e4627e1d'
down_revision = '8429068a8413'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event_inquiry', sa.Column('comment', sa.String(length=256), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_event_inquiry', 'comment')
    # ### end Alembic commands ###