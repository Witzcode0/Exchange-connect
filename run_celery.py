from app import make_celery, create_app

flaskapp = create_app('config', socket=True, main=False)

celery = make_celery(flaskapp)
