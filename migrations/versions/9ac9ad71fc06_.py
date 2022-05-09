"""empty message

Revision ID: 9ac9ad71fc06
Revises: 7b9045d92065
Create Date: 2018-02-28 10:39:02.641638

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9ac9ad71fc06'
down_revision = '7b9045d92065'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('corporate_access_event_inquiry_corporate_access_event_slot_id_f', 'corporate_access_event_inquiry', type_='foreignkey')
    op.create_foreign_key('cracs_event_inquiry_corporate_access_event_slot_id_fkey', 'corporate_access_event_inquiry', 'corporate_access_event_slot', ['corporate_access_event_slot_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('corporate_access_event_attendee_corporate_access_event_slot_id_', 'corporate_access_event_attendee', type_='foreignkey')
    op.create_foreign_key('cracs_event_attendee_corporate_access_event_slot_id_fkey', 'corporate_access_event_attendee', 'corporate_access_event_slot', ['corporate_access_event_slot_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('corporate_access_event_participant_corporate_access_event_id_fk', 'corporate_access_event_participant', type_='foreignkey')
    op.create_foreign_key('cracs_event_participant_corporate_access_event_id_fkey', 'corporate_access_event_participant', 'corporate_access_event', ['corporate_access_event_id'], ['id'], ondelete='CASCADE')


def downgrade():
    op.drop_constraint('cracs_event_inquiry_corporate_access_event_slot_id_fkey', 'corporate_access_event_inquiry', type_='foreignkey')
    op.create_foreign_key('corporate_access_event_inquiry_corporate_access_event_slot_id_f', 'corporate_access_event_inquiry', 'corporate_access_event_slot', ['corporate_access_event_slot_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('cracs_event_attendee_corporate_access_event_slot_id_fkey', 'corporate_access_event_attendee', type_='foreignkey')
    op.create_foreign_key('corporate_access_event_attendee_corporate_access_event_slot_id_', 'corporate_access_event_attendee', 'corporate_access_event_slot', ['corporate_access_event_slot_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('cracs_event_participant_corporate_access_event_id_fkey', 'corporate_access_event_participant', type_='foreignkey')
    op.create_foreign_key('corporate_access_event_participant_corporate_access_event_id_fk', 'corporate_access_event_participant', 'corporate_access_event', ['corporate_access_event_id'], ['id'], ondelete='CASCADE')
