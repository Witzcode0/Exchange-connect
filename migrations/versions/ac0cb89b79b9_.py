"""empty message

Revision ID: ac0cb89b79b9
Revises: 90134cc29cae
Create Date: 2020-02-11 15:29:45.440965

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ac0cb89b79b9'
down_revision = '0fa096bc5de8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('news_item', sa.Column('image_url', sa.String(length=1024), nullable=True))
    op.add_column('news_item', sa.Column('short_desc', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('news_item', 'short_desc')
    op.drop_column('news_item', 'image_url')
    # ### end Alembic commands ###