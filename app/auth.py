from datetime import datetime

from flask import session, redirect, url_for, flash, render_template, request, jsonify, g
from functools import wraps

from app import app
from app.error_messages import ErrorMessages
from app import repository

# save user_id to blacklist, use for force logout
session_blacklist = set()


def login_required(f):
    """
    check if user is logged in
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json:
                return jsonify({"error": ErrorMessages.LOGIN_REQUIRED}), 401
            flash(ErrorMessages.LOGIN_REQUIRED, "warning")
            return redirect(url_for("root"))

        # check if user is in blacklist
        if session.get("user_id") in session_blacklist:
            session.clear()
            if request.is_json:
                return jsonify({"error": ErrorMessages.RE_LOGIN}), 401
            # return to login page
            flash(ErrorMessages.RE_LOGIN, "warning")
            return redirect(url_for("root"))

        return f(*args, **kwargs)

    return decorated_function


def role_required(*roles):
    """
    check if user has the required role
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "role" not in session or session["role"] not in roles:
                return render_template("access_denied.html"), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def force_logout(user_id):
    """
    Add user_id to session_blacklist, force user to re-login
    """
    session_blacklist.add(user_id)

# Add a datetime filter
@app.template_filter('datetime')
def format_datetime(value):
    if value is None:
        return ""
    if isinstance(value, str):
        value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return value.strftime('%Y-%m-%d %H:%M')

# Add global template variables
@app.before_request
def before_request():
    if 'user_id' in session:
        g.unread_messages_count = repository.get_unread_messages_count(session['user_id'])
    else:
        g.unread_messages_count = 0

@app.context_processor
def inject_unread_messages():
    return dict(unread_messages_count=g.get('unread_messages_count', 0))
