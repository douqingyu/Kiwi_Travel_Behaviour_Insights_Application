from flask import request, jsonify, session

from app import app
from app import repository
from app.auth import login_required, role_required
from app.enums.role_enum import Role


@app.route('/location/list', methods=['POST'])
def get_locations():
    """
    Get all locations
    """
    locations = repository.get_locations()
    return {'success': True, "locations": locations}

@app.route('/location/follow', methods=['POST'])
@login_required
def follow_location():
    """
    Follow or unfollow a location
    """
    try:
        location_name = request.form.get('location_name')
        location_id = request.form.get('location_id')
        
        # Get current user ID
        user_id = session.get('user_id')
        # get current user
        current_user = repository.get_user_by_id(user_id)
        if not current_user:
            return jsonify({
                'success': False,
                'message': '用户未登录'
            }), 401

        # get location detail
        location = None
        if location_name:
            location = repository.get_location_by_name(location_name)
        elif location_id:
            location = repository.get_location_by_id(location_id)
            
        if not location:
            return jsonify({
                'success': False,
                'message': 'Can not find selected location!'
            }), 404

        # check if followed
        is_following = repository.is_following_location(user_id, location['id'])
        
        if is_following:
            # unfollow
            repository.unfollow_location(user_id, location['id'])
            is_following = False
        else:
            # follow
            repository.follow_location(user_id, location['id'])
            is_following = True

        return jsonify({
            'success': True,
            'is_following': is_following,
            'message': 'followed' if is_following else 'unfollowed'
        })

    except Exception as e:
        app.logger.error(f"Error in follow_location: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'system error'
        }), 500

# location_management
@app.route('/location/management', methods=['GET', 'POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def location_management():
    # get filter parameters
    keyword = request.form.get('keyword', None)
    current_page = int(request.form.get('page', 1))
    per_page = 12
    repository.get_location_page(keyword, current_page, per_page)


