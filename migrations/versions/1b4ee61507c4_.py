"""empty message

Revision ID: 1b4ee61507c4
Revises: eb7c33f1b04e
Create Date: 2018-04-03 18:07:01.946060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b4ee61507c4'
down_revision = 'eb7c33f1b04e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('webcast_attendee', sa.Column('comment', sa.String(length=256), nullable=True))
    op.add_column('webcast_attendee', sa.Column('created_by', sa.BigInteger(), nullable=False))
    op.add_column('webcast_attendee', sa.Column('updated_by', sa.BigInteger(), nullable=False))
    op.create_foreign_key('webcast_attendee_created_by_fkey', 'webcast_attendee', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('webcast_attendee_updated_by_fkey', 'webcast_attendee', 'user', ['updated_by'], ['id'], ondelete='CASCADE')
    op.add_column('webinar_attendee', sa.Column('comment', sa.String(length=256), nullable=True))
    op.add_column('webinar_attendee', sa.Column('created_by', sa.BigInteger(), nullable=False))
    op.add_column('webinar_attendee', sa.Column('updated_by', sa.BigInteger(), nullable=False))
    op.create_foreign_key('webinar_attendee_created_by_fkey', 'webinar_attendee', 'user', ['created_by'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('webinar_attendee_updated_by_fkey', 'webinar_attendee', 'user', ['updated_by'], ['id'], ondelete='CASCADE')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('webinar_attendee_updated_by_fkey', 'webinar_attendee', type_='foreignkey')
    op.drop_constraint('webinar_attendee_created_by_fkey', 'webinar_attendee', type_='foreignkey')
    op.drop_column('webinar_attendee', 'updated_by')
    op.drop_column('webinar_attendee', 'created_by')
    op.drop_column('webinar_attendee', 'comment')
    op.drop_constraint('webcast_attendee_updated_by_fkey', 'webcast_attendee', type_='foreignkey')
    op.drop_constraint('webcast_attendee_created_by_fkey', 'webcast_attendee', type_='foreignkey')
    op.drop_column('webcast_attendee', 'updated_by')
    op.drop_column('webcast_attendee', 'created_by')
    op.drop_column('webcast_attendee', 'comment')
    # ### end Alembic commands ###
