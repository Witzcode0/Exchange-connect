"""
Helpers for "project" package
"""

from flask import current_app
from sqlalchemy import func

from app import db
from app.toolkit_resources.project_parameters.models import ProjectParameter
from app.toolkit_resources.projects.models import Project
from app.toolkit_resources.project_status.models import ProjectStatus


def calculate_status(project):
    """
    used for status calculations for project module
    :param project:
        project instance for which status are to be calculated
    """
    try:
        # status calculate and update in project table
        max_seq = db.session.query(
            func.max(ProjectStatus.sequence)).first()[0]
        project.percentage = project.status.sequence / max_seq * 100
        if project.percentage == 100:
            project.is_completed = True
        db.session.add(project)
        db.session.commit()

    except Exception as e:
        current_app.logger.exception(e)
        raise e
    return
