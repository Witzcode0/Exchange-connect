"""empty message

Revision ID: f4a3ce445102
Revises: d8c5f83101b6
Create Date: 2018-04-02 15:34:01.338338

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4a3ce445102'
down_revision = 'd8c5f83101b6'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('project_analyst_project_id_fkey', 'project_analyst', type_='foreignkey')
    op.create_foreign_key('project_analyst_project_id_fkey', 'project_analyst', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('project_archive_file_project_id_fkey', 'project_archive_file', type_='foreignkey')
    op.create_foreign_key('project_archive_file_project_id_fkey', 'project_archive_file', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('project_chat_message_project_id_fkey', 'project_chat_message', type_='foreignkey')
    op.create_foreign_key('project_chat_message_project_id_fkey', 'project_chat_message', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('project_parameter_project_id_fkey', 'project_parameter', type_='foreignkey')
    op.create_foreign_key('project_parameter_project_id_fkey', 'project_parameter', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.drop_constraint('project_screen_sharing_project_id_fkey', 'project_screen_sharing', type_='foreignkey')
    op.create_foreign_key('project_screen_sharing_project_id_fkey', 'project_screen_sharing', 'project', ['project_id'], ['id'], ondelete='CASCADE')
    op.add_column('ref_project_type', sa.Column('deleted', sa.Boolean(), nullable=True))
    op.execute("UPDATE ref_project_type SET deleted=false")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('ref_project_type', 'deleted')
    op.drop_constraint('project_screen_sharing_project_id_fkey', 'project_screen_sharing', type_='foreignkey')
    op.create_foreign_key('project_screen_sharing_project_id_fkey', 'project_screen_sharing', 'project', ['project_id'], ['id'])
    op.drop_constraint('project_parameter_project_id_fkey', 'project_parameter', type_='foreignkey')
    op.create_foreign_key('project_parameter_project_id_fkey', 'project_parameter', 'project', ['project_id'], ['id'])
    op.drop_constraint('project_chat_message_project_id_fkey', 'project_chat_message', type_='foreignkey')
    op.create_foreign_key('project_chat_message_project_id_fkey', 'project_chat_message', 'project', ['project_id'], ['id'])
    op.drop_constraint('project_archive_file_project_id_fkey', 'project_archive_file', type_='foreignkey')
    op.create_foreign_key('project_archive_file_project_id_fkey', 'project_archive_file', 'project', ['project_id'], ['id'])
    op.drop_constraint('project_analyst_project_id_fkey', 'project_analyst', type_='foreignkey')
    op.create_foreign_key('project_analyst_project_id_fkey', 'project_analyst', 'project', ['project_id'], ['id'])
    # ### end Alembic commands ###
