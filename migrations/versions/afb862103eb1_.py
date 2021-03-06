"""empty message

Revision ID: afb862103eb1
Revises: b8ed07b30b65
Create Date: 2019-01-10 18:24:25.999854

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'afb862103eb1'
down_revision = 'b531b0e89736'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('news_item', sa.Column('tags', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('news_item_archive', sa.Column('tags', sa.ARRAY(sa.String()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('news_item', 'tags')
    op.drop_column('news_item_archive', 'tags')
    # ### end Alembic commands ###
