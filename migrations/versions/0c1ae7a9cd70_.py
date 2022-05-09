"""empty message

Revision ID: 0c1ae7a9cd70
Revises: 364aadd63031
Create Date: 2018-06-04 16:51:55.245734

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0c1ae7a9cd70'
down_revision = '364aadd63031'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('account', 'created_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('account', 'updated_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('contact_history', 'sent_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('contact_history', 'sent_to',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('contact_request_history', 'sent_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('contact_request_history', 'sent_to',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('eventfiles', 'event_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('follow_history', 'company_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('follow_history', 'sent_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('postfiles', 'file_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('postfiles', 'post_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('registration_request', 'updated_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True)
    op.alter_column('role', 'created_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('role', 'updated_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('survey_response', 'survey_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('survey_response', 'user_id',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=True)
    op.alter_column('user', 'created_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.alter_column('user', 'updated_by',
               existing_type=sa.INTEGER(),
               type_=sa.BigInteger(),
               existing_nullable=False)
    op.add_column('webinar', sa.Column('cancelled', sa.Boolean(), nullable=True))
    op.execute("UPDATE webinar SET cancelled=false")
    op.add_column('webinar_participant', sa.Column('sequence_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('c_wbnpr_webinar_id_sequence_id_key', 'webinar_participant', ['webinar_id', 'sequence_id'])
    op.add_column('webinar_rsvp', sa.Column('sequence_id', sa.Integer(), nullable=True))
    op.create_unique_constraint('c_wbnrp_webinar_id_sequence_id_key', 'webinar_rsvp', ['webinar_id', 'sequence_id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('c_wbnrp_webinar_id_sequence_id_key', 'webinar_rsvp', type_='unique')
    op.drop_column('webinar_rsvp', 'sequence_id')
    op.drop_constraint('c_wbnpr_webinar_id_sequence_id_key', 'webinar_participant', type_='unique')
    op.drop_column('webinar_participant', 'sequence_id')
    op.drop_column('webinar', 'cancelled')
    op.alter_column('user', 'updated_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('user', 'created_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('survey_response', 'user_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('survey_response', 'survey_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('role', 'updated_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('role', 'created_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('registration_request', 'updated_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=True)
    op.alter_column('postfiles', 'post_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('postfiles', 'file_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('follow_history', 'sent_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('follow_history', 'company_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('eventfiles', 'event_id',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('contact_request_history', 'sent_to',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('contact_request_history', 'sent_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('contact_history', 'sent_to',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('contact_history', 'sent_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('account', 'updated_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.alter_column('account', 'created_by',
               existing_type=sa.BigInteger(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    # ### end Alembic commands ###
