"""
Helper classes/functions for "emails" package.
"""

from app.resources.email_credentials.models import EmailCredential


def get_smtp_settings(user_id):
    email_cred = EmailCredential.query.filter(
        EmailCredential.created_by==user_id).first()
    if not email_cred:
        return {}
    return email_cred.get_smtp_settings()
