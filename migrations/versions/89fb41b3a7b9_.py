"""empty message

Revision ID: 89fb41b3a7b9
Revises: 519eda76c617
Create Date: 2018-10-03 11:44:20.935218

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '89fb41b3a7b9'
down_revision = '3af9dee0bd41'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event', sa.Column('caevent_support', sa.Boolean(), nullable=True))
    op.execute("UPDATE corporate_access_event SET caevent_support=false")
    op.add_column('corporate_access_event', sa.Column('flexibility', sa.Boolean(), nullable=True))
    op.execute("UPDATE corporate_access_event SET flexibility=false")
    op.add_column('corporate_access_event', sa.Column('remark', sa.String(length=2048), nullable=True))
    op.add_column('corporate_access_event', sa.Column('other_invitees', sa.String(length=2048), nullable=True))
    op.add_column('corporate_access_ref_event_type', sa.Column('is_meeting', sa.Boolean(), nullable=True))
    op.execute("UPDATE corporate_access_ref_event_type SET is_meeting=false")
    op.add_column('notification', sa.Column('corporate_access_event_invitee_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key('notification_ca_event_invitee_id_fkey', 'notification', 'corporate_access_event_invitee', ['corporate_access_event_invitee_id'], ['id'], ondelete='CASCADE')
    op.add_column('corporate_access_event_invitee', sa.Column('invitee_remark', sa.String(length=2048), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('corporate_access_ref_event_type', 'is_meeting')
    op.drop_column('corporate_access_event', 'remark')
    op.drop_column('corporate_access_event', 'other_invitees')
    op.drop_column('corporate_access_event', 'flexibility')
    op.drop_column('corporate_access_event', 'caevent_support')
    op.drop_constraint('notification_ca_event_invitee_id_fkey', 'notification', type_='foreignkey')
    op.drop_column('notification', 'corporate_access_event_invitee_id')
    op.drop_column('corporate_access_event_invitee', 'invitee_remark')
    # ### end Alembic commands ###