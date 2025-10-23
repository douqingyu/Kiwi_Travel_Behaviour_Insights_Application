from app import app, repository
from flask import jsonify, request, session
from app.auth import login_required, role_required
from app.enums.role_enum import Role


@app.route('/announcement/submit', methods=['POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def announcement_submit():
    """
    Submit a new announcement
    Only admin can submit announcements
    """
    try:
        data = request.get_json()
        title = data.get('title')
        content = data.get('content')
        
        if not title or not content:
            return jsonify({'error': 'Title and content are required'}), 400
            
        user_id = session.get('user_id')
        announcement_id = repository.create_announcement(user_id, title, content)
        
        return jsonify({
            'success': True,
            'message': 'Announcement created successfully',
            'announcement_id': announcement_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500 