"""
Users Stats related tasks
"""

from sqlalchemy.orm import load_only

from app import db
from app.resources.users.models import User
from app.resources.users import constants as USER

from queueapp.tasks import celery_app, logger


@celery_app.task(bind=True, ignore_result=True)
def manage_users_stats(self, result, user_ids, stats, increase=True,
                       *args, **kwargs):
    """
    Update users stats such as total_files, total_video, total_companies,
    total_contacts when user perform file upload, contact accept or delete etc

    :param result:
        the result of previous task when chaining. Remember to pass True, when
        called as first of chain, or individually.
    :param user_id:
        id of user who is uploading files or accepting contact etc
    :param stats:
        stats is type such as files/video/contact/companies
    :param increase:
        increase is a boolean True for increase by 1 and False for decrease
    """

    if result:
        try:
            if not isinstance(user_ids, list):
                user_ids =[user_ids]

            for user_id in user_ids:
                user_data = User.query.filter(
                    User.row_id == user_id).options(load_only(
                        'row_id', 'total_files', 'total_videos',
                        'total_companies', 'total_contacts')).first()
                if not user_data:
                    continue

                if stats == USER.USR_FILES:
                    if not user_data.total_files:
                        user_data.total_files = 0
                    if increase:
                        user_data.total_files += 1
                    else:
                        if user_data.total_files:
                            user_data.total_files -= 1
                elif stats == USER.USR_VIDEOS:
                    if not user_data.total_videos:
                        user_data.total_videos = 0
                    if increase:
                        user_data.total_videos += 1
                    else:
                        if user_data.total_videos:
                            user_data.total_videos -= 1
                elif stats == USER.USR_CONTS:
                    if not user_data.total_contacts:
                        user_data.total_contacts = 0
                    if increase:
                        user_data.total_contacts += 1
                    else:
                        if user_data.total_contacts:
                            user_data.total_contacts -= 1
                elif stats == USER.USR_COMPS:
                    if not user_data.total_companies:
                        user_data.total_companies = 0
                    if increase:
                        user_data.total_companies += 1
                    else:
                        if user_data.total_companies:
                            user_data.total_companies -= 1

                db.session.add(user_data)
                db.session.commit()
            result = True
        except Exception as e:
            db.session.rollback()
            logger.exception(e)
            result = False

        return result
