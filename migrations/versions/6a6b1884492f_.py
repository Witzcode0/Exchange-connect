"""empty message

Revision ID: 6a6b1884492f
Revises: efdacd2d75db
Create Date: 2019-12-09 11:23:05.167180

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import app
from app.toolkit_resources.projects import constants as PROJ


# revision identifiers, used by Alembic.
revision = '6a6b1884492f'
down_revision = '67bdae182cad'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.execute("insert into project_status(id, created_by, updated_by, name, code, sequence) values(1,1,1,'Project assigned', 'proj_assigned', 1);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(2,1,1,'Introductory call', 'intro_call', 2);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(3,1,1,'Template designing', 'template_designing', 3);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(4,1,1,'Template received', 'template_received', 4);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(5,1,1,'Template approved', 'template_approved', 5);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(6,1,1,'Main presentation', 'main_presentation', 6);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(7,1,1,'Presentation received', 'presentation_received', 7);")
    op.execute(
        "insert into project_status(id, created_by, updated_by, name, code, sequence) values(8,1,1,'Completed', 'completed', 8);")
    op.execute("update project_status set created_date = current_timestamp, modified_date=current_timestamp")
    op.add_column('project',
                  sa.Column(
                      'dimention', app.base.model_fields.ChoiceString(PROJ.DIMENTION_TYPES_CHOICES),
                      nullable=False, server_default=PROJ.STANDARD))
    op.add_column('project', sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('project', sa.Column('sides_nr', sa.Integer(), nullable=True))
    op.add_column('project', sa.Column('status_id', sa.BigInteger(), nullable=False, server_default='1'))
    op.add_column('project', sa.Column(
        'work_area', app.base.model_fields.ChoiceString(
            PROJ.WORK_ARIA_CHOICES), nullable=False, server_default=PROJ.DESIGN))
    op.create_foreign_key('project_status_id_fkey', 'project', 'project_status', ['status_id'], ['id'])
    op.add_column('project',
                  sa.Column('percentage', sa.Numeric(precision=5, scale=2),
                            server_default='0', nullable=True))
    op.drop_column('project', 'status')
    op.add_column('project_archive_file', sa.Column('category',
                                                    app.base.model_fields.ChoiceString(
                                                        PROJ.PROJECT_FILE_CATEGORY_CHOICES),
                                                    nullable=True))
    op.add_column('project',
                  sa.Column('is_completed', sa.Boolean(), nullable=False,
                            server_default='0'))
    op.add_column('project', sa.Column('questionnaire',
                                       postgresql.JSONB(astext_type=sa.Text()),
                                       nullable=True))
    op.add_column('project_archive_file',
                  sa.Column('is_approved', sa.Boolean(), server_default='0',
                            nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('project_status_id_fkey', 'project', type_='foreignkey')
    op.drop_column('project', 'work_area')
    op.drop_column('project', 'status_id')
    op.drop_column('project', 'sides_nr')
    op.drop_column('project', 'params')
    op.drop_column('project', 'dimention')
    op.add_column('project',
                  sa.Column('status', sa.NUMERIC(precision=5, scale=2),
                            autoincrement=False, nullable=True))
    op.drop_column('project', 'percentage')
    op.drop_column('project_archive_file', 'category')
    op.drop_column('project', 'is_completed')
    op.drop_column('project', 'questionnaire')
    op.drop_column('project_archive_file', 'is_approved')
    # ### end Alembic commands ###
