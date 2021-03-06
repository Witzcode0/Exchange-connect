"""empty message

Revision ID: 62414a0cc9d4
Revises: f2d9d8f0644f
Create Date: 2018-04-09 16:56:20.112334

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62414a0cc9d4'
down_revision = 'f2d9d8f0644f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('newswire_post', sa.Column('logo_file_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('newswire_post_logo_file_id_fkey', 'newswire_post', 'newswire_post_library_file', ['logo_file_id'], ['id'])
    op.drop_column('newswire_post', 'logo_filename')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('newswire_post', sa.Column('logo_filename', sa.VARCHAR(length=256), autoincrement=False, nullable=True))
    op.drop_constraint('newswire_post_logo_file_id_fkey', 'newswire_post', type_='foreignkey')
    op.drop_column('newswire_post', 'logo_file_id')
    # ### end Alembic commands ###
