from app import app
from app import repository
from app.auth import login_required, session_blacklist, role_required
from app.enums.user_status_enum import UserStatus
from app.error_messages import ErrorMessages
from app.file import upload, allowed_file
from flask import redirect, render_template, request, session, url_for, flash, jsonify
from flask_bcrypt import Bcrypt
import os

from app.enums.role_enum import Role
from app.validate import validate_password, validate_username, validate_name, validate_location, validate_email

# Create an instance of the Bcrypt class, which we'll be using to hash user
# passwords during login and registration.
flask_bcrypt = Bcrypt(app)

# Default user role for new accounts.
DEFAULT_USER_ROLE = Role.TRAVELLER

def get_user_role():
    """get user role from session"""
    role = session.get('role', None)
    return Role.from_value(role) if role is not None else None

def user_home_url():
    """Generates a URL to the homepage for the currently logged-in user.

    If the user is not logged in, or the role stored in their session cookie is
    invalid, this returns the URL for the login page instead."""
    role_enum = get_user_role()
    if role_enum:
        home_endpoint = 'dashboard'
    else:
        home_endpoint = 'login'
    return url_for(home_endpoint)


@app.route('/')
def root():
    """Root endpoint (/)
    """
    # Get published journeys
    published_journeys, _, _ = repository.get_published_journeys_page(1, 9, False)
    
    if get_user_role():
        return redirect(url_for('dashboard'))
    return render_template('home.html', published_journeys=published_journeys)


@app.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard page showing user info and announcements
    """
    user_id = session.get('user_id')
    user = repository.get_user_by_id(user_id)
    announcements = repository.get_announcements()
    journeys = repository.get_newest_journeys_by_user_id(user_id)
    
    # Get journey and event counts
    journey_count = repository.get_user_journeys_count(user_id)
    event_count = repository.get_user_events_count(user_id)
    all_users_count = repository.get_all_users_count()
    public_journeys_count = repository.get_public_journeys_count()

    return render_template('dashboard.html',
                           user=user,
                           announcements=announcements,
                           journeys=journeys,
                           journey_count=journey_count,
                           event_count=event_count,
                           all_users_count=all_users_count,
                           public_journeys_count=public_journeys_count)


@app.route('/user/reset/password', methods=['POST'])
@login_required
def reset_password():
    """
    Reset user password.
    New password should be different from the old password.
    """
    data = request.get_json()
    user_id = session.get('user_id', None)
    password = data.get('old_password')
    new_password = data.get('password')

    # validate parameters
    if not password:
        return {'success': False, 'message': ErrorMessages.OLD_PASSWORD_REQUIRED}
    password_error = validate_password(new_password)
    if password_error:
        return {'success': False, 'message': password_error}
    if new_password == password:
        return {'success': False, 'message': ErrorMessages.PASSWORD_SAME}

    # check user old password
    user = repository.get_user_by_id(user_id)
    if not user:
        return {'success': False, 'message': ErrorMessages.ACCOUNT_NOT_FOUND}
    if not flask_bcrypt.check_password_hash(user['password_hash'], password):
        return {'success': False, 'message': ErrorMessages.INVALID_PASSWORD}

    # update user password
    new_password_hash = flask_bcrypt.generate_password_hash(new_password)
    repository.update_user_password(user_id, new_password_hash)

    return {'success': True}


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login. all users can access this endpoint to login.
    """
    if session.get('loggedin'):
        return redirect(user_home_url())

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # validate username and password
        error_messages = {
            'username_error': validate_username(username),
            'password_error': validate_password(password)
        }
        if any(error_messages.values()):
            return render_template('login.html', **request.form, **error_messages)

        account = repository.get_user_by_username(username)
        if not account:
            return render_template('login.html', **request.form, username_error=ErrorMessages.ACCOUNT_NOT_FOUND)

        # check if user is ACTIVE
        if account['status'] != UserStatus.ACTIVE.value:
            return render_template('login.html', **request.form, username_error=ErrorMessages.ACCOUNT_BANNED)

        # check password
        if not flask_bcrypt.check_password_hash(account['password_hash'], password):
            return render_template('login.html', **request.form, password_error=ErrorMessages.INVALID_PASSWORD)
        
        # get subscription details
        subscription = repository.get_latest_subscription_by_id(account['id'])

        # update user session
        update_user_session(account, subscription)
        # remove user_id from session_blacklist if exists
        if account['id'] in session_blacklist:
            session_blacklist.remove(account['id'])
        return redirect(user_home_url())

    return render_template('login.html')


def update_user_session(user, subscription):
    session.update({
        'loggedin': True,
        'user_id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'profile_image': user['profile_image'],
        'role': user['role'],
        'can_share': user['can_share'],
    })
    if subscription:
        session.update({
        'loggedin': True,
        'user_id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'profile_image': user['profile_image'],
        'role': user['role'],
        'can_share': user['can_share'],
        'plan_id': subscription['plan_id'],
        'start_date': subscription['start_date'],
        'end_date': subscription['end_date'],
        'payment_amount': subscription['payment_amount'],
        'gst_amount': subscription['gst_amount'],
        'billing_country': subscription['billing_country'],
        'is_free_trial': subscription['is_free_trial'],
        'granted_by_admin': subscription['granted_by_admin'],
        'created_at': subscription['created_at'],
    })


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    """Logout endpoint.

    Methods:
    - GET/POST: Logs the current user out (if they were logged in to begin with),
        and returns a JSON response indicating success.
    """
    session.pop('loggedin', None)
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('email', None)
    session.pop('first_name', None)
    session.pop('last_name', None)
    session.pop('profile_image', None)
    session.pop('role', None)
    session.pop('can_share', None)
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Signup (registration) page endpoint.
    All users can access this endpoint to signup.
    Default role is TRAVELLER.
    """
    if 'loggedin' in session:
        return redirect(user_home_url())

    if request.method == 'POST' and 'username' in request.form and 'email' in request.form and 'password' in request.form:
        # Get the details submitted via the form on the signup page, and store
        # the values in temporary local variables for ease of access.
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        location_name = request.form['location_name']
        email = request.form['email']
        password = request.form['password']

        # validate the form data
        username_error = validate_username(username)
        if not username_error:
            account_already_exists = repository.get_user_by_username(username) is not None
            if account_already_exists:
                username_error = ErrorMessages.ACCOUNT_ALREADY_EXISTS
        email_error = validate_email(email)
        if not email_error:
            account_already_exists = repository.get_user_by_email(email) is not None
            if account_already_exists:
                email_error = ErrorMessages.EMAIL_ALREADY_EXISTS

        # Optional fields
        first_name_error = None
        if first_name:
            first_name_error = validate_name(first_name)
        last_name_error = None
        if last_name:
            last_name_error = validate_name(last_name)
        location_error = None
        if location_name:
            location_error = validate_location(location_name)

        error_messages = {
            'username_error': username_error,
            'first_name_error': first_name_error,
            'last_name_error': last_name_error,
            'location_error': location_error,
            'email_error': email_error,
            'password_error': validate_password(password)
        }

        if any(error_messages.values()):
            return render_template('signup.html', **request.form, **error_messages)
        else:
            password_hash = flask_bcrypt.generate_password_hash(password)
            # select location_id
            location_id = repository.get_or_create_location_id(location_name)

            # create a new user account in the database
            user_id = repository.create_user(username, password_hash, email, first_name, last_name, location_id,
                                   DEFAULT_USER_ROLE.value)
            # signup successful message
            flash(ErrorMessages.SIGNUP_SUCCESS, "success")

            return render_template('login.html', username=username)

    return render_template('signup.html')


@app.route('/profile')
@login_required
def profile():
    """View your own profile page"""
    user = repository.get_user_by_id(session['user_id'])
    location = repository.get_location_by_id(user['location_id']) if user['location_id'] else None
    return render_template('user_profile.html',
                         user=user,
                         username=user['username'],
                         email=user['email'],
                         first_name=user['first_name'],
                         last_name=user['last_name'],
                         location_name=location['name'] if location else None,
                         description=user['description'],
                         profile_image=user['profile_image'],
                         is_own_profile=True)


@app.route('/profile/<int:user_id>')
@login_required
def view_profile(user_id):
    """View others' profile page."""
    user = repository.get_user_by_id(user_id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))
        
    location = repository.get_location_by_id(user['location_id']) if user['location_id'] else None
    
    # Check if it's your own profile page
    is_own_profile = session.get('user_id') == user['id']
    
    # If it's not your own profile page, check the follow status
    is_following = False
    if not is_own_profile:
        current_user_id = session.get('user_id')
        is_following = repository.check_user_follow_status(user['id'], current_user_id)
    
    return render_template('user_profile.html',
                         user=user,
                         username=user['username'],
                         email=user['email'],
                         first_name=user['first_name'],
                         last_name=user['last_name'],
                         location_name=location['name'] if location else None,
                         description=user['description'],
                         profile_image=user['profile_image'],
                         is_own_profile=is_own_profile,
                         is_following=is_following)


@app.route('/profile/save', methods=['POST'])
@login_required
def save_profile():
    """Save user profile"""
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    location_id = request.form.get('location_id')
    description = request.form.get('description')
    
    # Verify if the email has been used by another user
    existing_user = repository.get_user_by_email(email)
    if existing_user and existing_user['id'] != session['user_id']:
        flash('Email already exists', 'error')
        return redirect(url_for('profile'))
    
    # update user profile
    repository.update_user_profile(
        session['user_id'],
        email,
        first_name,
        last_name,
        location_id,
        description
    )
    
    # update detail in session
    session['email'] = email
    session['first_name'] = first_name
    session['last_name'] = last_name
    
    flash('Profile updated successfully', 'success')
    return redirect(url_for('profile'))


@app.route('/profile/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """upload avatar"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('profile'))
        
    if file and allowed_file(file.filename):
        # Generate a unique filename
        filename = upload(file, prefix='avatar')
        
        # file.save(file_path)
        
        # Update avatar path in the database
        repository.update_user_profile_image(session['user_id'], filename)
        
        # Update avatar path in the session
        session['profile_image'] = filename
        
        flash('Avatar uploaded successfully', 'success')
    else:
        flash('Invalid file type', 'error')
        
    return redirect(url_for('profile'))


@app.route('/profile/delete-avatar', methods=['POST'])
@login_required
def delete_avatar():
    """delete avatar"""
    user = repository.get_user_by_id(session['user_id'])
    if user['profile_image']:
        # delete file
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], user['profile_image'])
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # update database
        repository.update_user_profile_image(session['user_id'], None)
        
        # update session
        session['profile_image'] = None
        
        flash('Avatar deleted successfully', 'success')
    else:
        flash('No avatar to delete', 'error')
        
    return redirect(url_for('profile'))


@app.route('/user/detail', methods=['GET', 'POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value, Role.EDITOR.value)
def user_detail():
    """
    Retrieve user details by user_id.
    Accessible only to admin and editor roles.
    Returns: user details，without password_hash.
    """
    data = request.get_json()
    user_id = data.get('user_id', None)
    if not user_id:
        return {'success': False, 'message': ErrorMessages.USER_ID_REQUIRED}

    # Retrieve user profile from the database.
    user = repository.get_user_by_id(user_id)
    # Remove password hash (Don't want to show this in the UI)
    user.pop('password_hash', None)
    # get location name
    location = repository.get_location_by_id(user['location_id'])
    # check if location is None
    if location:
        user['location_name'] = location['name']
    else:
        user['location_name'] = ''

    return {'success': True, 'user': user}


@app.route('/users/search')
@login_required
def user_search():
    """用户搜索页面"""
    # get search param
    keyword = request.args.get('keyword', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # get user list
    users, total, total_pages = repository.get_public_users_page(
        keyword=keyword,
        page=page,
        per_page=per_page
    )

    return render_template('user_search.html',
                         users=users,
                         total=total,
                         total_pages=total_pages,
                         current_page=page,
                         keyword=keyword,
                         active_page='users')


@app.route('/profile/visibility', methods=['POST'])
@login_required
def update_profile_visibility():
    """Update user profile visibility settings in the public directory"""
    data = request.get_json()
    is_public = data.get('is_public', True)
    
    # Update user visibility settings
    repository.update_user_profile_visibility(session['user_id'], is_public)
    
    return jsonify({
        'success': True,
        'message': 'Profile visibility updated successfully'
    })


@app.route('/profile/events')
@login_required
def get_profile_events():
    """Get user event feed (based on event table)"""
    try:
        user_id = request.args.get('user_id', session['user_id'])
        page = request.args.get('page', 1, type=int)
        is_own_profile = str(user_id) == str(session['user_id'])
        
        print(f"Debug - Getting events for user_id: {user_id}, page: {page}")
        
        # Only query public events when it's not your own
        only_public = not is_own_profile
        events, total, total_pages = repository.get_user_events(user_id, page, only_public=only_public)
        visited_places = repository.get_user_visited_places(user_id)
        
        print(f"Debug - Found {len(events) if events else 0} events")
        print(f"Debug - Found {len(visited_places) if visited_places else 0} visited places")
        
        return jsonify({
            'success': True,
            'events': events,
            'visited_places': visited_places,
            'is_own_profile': is_own_profile,
            'total': total,
            'total_pages': total_pages,
            'current_page': page
        })
    except Exception as e:
        print(f"Debug - Error in get_profile_events: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load events. Please try again later.'
        }), 500
    
@app.route('/following')
@login_required
def following():
    """Get user following list"""
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    
    # Get a list of users followed by the user
    followed_users = repository.get_followed_users(user_id)
    
    # Get a list of locations followed by the user.
    followed_locations = repository.get_followed_locations(user_id)
    
    return render_template('following.html', 
                         followed_users=followed_users,
                         followed_locations=followed_locations)

@app.route('/user/follow', methods=['POST'])
@login_required
def toggle_user_follow():
    """
    follow/unfollow user
    """
    try:
        user_id = request.form.get('user_id')
        follower_id = session.get('user_id')
        
        # Record request data
        app.logger.info(f"Follow request - user_id: {user_id}, follower_id: {follower_id}")
        
        if not user_id:
            app.logger.error("Missing user_id in request")
            return {'success': False, 'message': 'system error'}
            
        if not follower_id:
            app.logger.error("Missing follower_id in session")
            return {'success': False, 'message': 'need to login'}
        
        # check if user exists
        user = repository.get_user_by_id(user_id)
        if not user:
            app.logger.error(f"User not found - user_id: {user_id}")
            return {'success': False, 'message': 'user does not exist'}
        
        # Check if it's a premium user or staff
        follower = repository.get_user_by_id(follower_id)
        if not follower:
            app.logger.error(f"Follower not found - follower_id: {follower_id}")
            return {'success': False, 'message': 'Follower does not exist'}
            
        is_premium = repository.get_current_subscription(follower_id) is not None
        is_staff = follower['role'] in ['admin', 'editor', 'support_techs']
        
        if not (is_premium or is_staff):
            app.logger.warning(f"Non-premium user attempted to follow - follower_id: {follower_id}")
            return {'success': False, 'message': 'system error'}
        
        # update follow status
        is_following = repository.toggle_user_follow(user_id, follower_id)
        app.logger.info(f"Follow status toggled - user_id: {user_id}, follower_id: {follower_id}, is_following: {is_following}")
        
        return {
            'success': True,
            'is_following': is_following
        }
        
    except Exception as e:
        app.logger.error(f"Error in toggle_user_follow: {str(e)}")
        return {'success': False, 'message': 'system error'}
