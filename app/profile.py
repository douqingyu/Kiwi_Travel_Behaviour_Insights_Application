@app.route('/profile/<username>')
@login_required
def user_profile(username):
    """
    User profile page
    """
    user = repository.get_user_by_username(username)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('index'))
    
    # Get the user's location information
    location = repository.get_location_by_id(user['location_id']) if user['location_id'] else None
    location_name = location['name'] if location else None
    
    # Check if it is your own profile page
    is_own_profile = session.get('user_id') == user['id']
    
    # If it is not your own profile page, check the follow status
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
                         location_name=location_name,
                         description=user['description'],
                         profile_image=user['profile_image'],
                         is_own_profile=is_own_profile,
                         is_following=is_following) 