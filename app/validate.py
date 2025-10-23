import re

from app.error_messages import ErrorMessages
from app.regex_patterns import USERNAME_PATTERN, EMAIL_PATTERN, PASSWORD_PATTERN, NAME_PATTERN


def validate_username(username):
    """
    Check whether the username is valid
    """
    if not username:
        return ErrorMessages.USERNAME_REQUIRED
    # Check whether there's an account with this username in the database.
    if not re.match(USERNAME_PATTERN, username):
        return ErrorMessages.INVALID_USERNAME
    return None


def validate_email(email):
    """
    Check whether the email is valid
    """
    if len(email) > 320:
        return ErrorMessages.EMAIL_TOO_LONG
    if not re.match(EMAIL_PATTERN, email):
        return ErrorMessages.INVALID_EMAIL
    return None


def validate_password(password):
    """
    Check whether the password is valid
    """
    if not password:
        return ErrorMessages.PASSWORD_REQUIRED
    if not re.match(PASSWORD_PATTERN, password):
        return ErrorMessages.INVALID_PASSWORD_FORMAT
    return None


def validate_name(name):
    """
    Check whether the name is valid
    """
    if not re.match(NAME_PATTERN, name):
        return ErrorMessages.INVALID_NAME
    return None


def validate_location(location):
    """
    Check whether the location is valid
    """
    if len(location) > 50:
        return ErrorMessages.LOCATION_TOO_LONG
    return None