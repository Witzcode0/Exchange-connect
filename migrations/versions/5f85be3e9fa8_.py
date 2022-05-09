"""empty message

Revision ID: 5f85be3e9fa8
Revises: 62414a0cc9d4
Create Date: 2018-04-13 14:31:44.188849

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f85be3e9fa8'
down_revision = '62414a0cc9d4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('corporate_access_event', sa.Column('alternative_dial_in_detail', sa.String(length=512), nullable=True))
    op.add_column('corporate_access_ref_event_sub_type', sa.Column('has_slots', sa.Boolean(), nullable=True))

    op.drop_constraint('corporate_access_ref_event_sub_type_name_key', 'corporate_access_ref_event_sub_type', type_='unique')
    op.drop_index('ci_corporate_access_ref_event_sub_type_unique_name')
    op.create_index('ci_corporate_access_ref_event_sub_type_unique_type_id_name', 'corporate_access_ref_event_sub_type', ['event_type_id', sa.text('lower(name)')], unique=True)

    op.drop_constraint('project_archive_file_project_parameter_id_fkey', 'project_archive_file', type_='foreignkey')
    op.create_foreign_key('project_archive_file_project_parameter_id_fkey', 'project_archive_file', 'project_parameter', ['project_parameter_id'], ['id'], ondelete='SET NULL')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('project_archive_file_project_parameter_id_fkey', 'project_archive_file', type_='foreignkey')
    op.create_foreign_key('project_archive_file_project_parameter_id_fkey', 'project_archive_file', 'project_parameter', ['project_parameter_id'], ['id'])

    op.create_unique_constraint('corporate_access_ref_event_sub_type_name_key', 'corporate_access_ref_event_sub_type', ['name'])
    op.drop_index('ci_corporate_access_ref_event_sub_type_unique_type_id_name')
    op.create_index('ci_corporate_access_ref_event_sub_type_unique_name', 'corporate_access_ref_event_sub_type', [sa.text('lower(name)')], unique=True)

    op.drop_column('corporate_access_ref_event_sub_type', 'has_slots')
    op.drop_column('corporate_access_event', 'alternative_dial_in_detail')
    # ### end Alembic commands ###