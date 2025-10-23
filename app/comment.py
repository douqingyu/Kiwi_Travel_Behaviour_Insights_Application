from app import app, repository
from flask import redirect, render_template, session, url_for, request, flash, jsonify

from app.auth import login_required
from app.error_messages import ErrorMessages
from app.file import allowed_file, upload


@app.route('/comment/submit', methods=['POST'])
@login_required
def comment_submit():
    """
    Add a new comment
    """
    data = request.get_json()
    event_id = data.get('event_id')
    content = data.get('content')
    
    if not event_id or not content:
        return {'success': False, 'error': 'Missing required fields'}, 400
        
    # Get current user ID
    user_id = session.get('user_id')
    
    # Create comment
    comment_id = repository.create_comment(event_id, user_id, content)
    
    return {'success': True, 'comment_id': comment_id}


@app.route('/comment/list', methods=['GET'])
@login_required
def comment_list():
    """
    Get comments for an event with sorting options
    """
    event_id = request.args.get('event_id')
    sort_by = request.args.get('sort_by', 'newest')  # Default to newest
    
    if not event_id:
        return {'success': False, 'error': 'Missing event_id'}, 400
        
    # Get current user ID
    user_id = session.get('user_id')
        
    # Get comments with user information
    comments = repository.get_comments_by_event_id(event_id, user_id, sort_by)
    
    return {'success': True, 'comments': comments}


@app.route('/comment/delete', methods=['POST'])
@login_required
def comment_delete():
    """
    Delete a comment
    """
    data = request.get_json()
    comment_id = data.get('comment_id')
    
    if not comment_id:
        return {'success': False, 'error': 'Missing comment_id'}, 400
        
    # Get current user ID and role
    user_id = session.get('user_id')
    user_role = session.get('role')
    
    # Get comment information
    comment = repository.get_comment_by_id(comment_id)
    if not comment:
        return {'success': False, 'error': 'Comment not found'}, 404
        
    # Check if user has permission to delete
    if str(user_id) != str(comment['user_id']) and user_role not in ['admin', 'editor']:
        return {'success': False, 'error': 'Permission denied'}, 403
        
    # Delete comment
    repository.delete_comment(comment_id)
    
    return {'success': True}


@app.route('/comment/react', methods=['POST'])
@login_required
def comment_react():
    """
    Add or remove a reaction (like/dislike) to a comment
    """
    data = request.get_json()
    comment_id = data.get('comment_id')
    reaction_type = data.get('reaction_type')
    
    if not comment_id or not reaction_type:
        return {'success': False, 'error': 'Missing required fields'}, 400
        
    if reaction_type not in ['like', 'dislike']:
        return {'success': False, 'error': 'Invalid reaction type'}, 400
        
    # Get current user ID
    user_id = session.get('user_id')
    
    # Toggle reaction
    result = repository.toggle_comment_reaction(comment_id, user_id, reaction_type)
    
    return {'success': True, 'action': result}


@app.route('/comment/reactions', methods=['GET'])
@login_required
def comment_reactions():
    """
    Get reactions for a comment
    """
    comment_id = request.args.get('comment_id')
    
    if not comment_id:
        return {'success': False, 'error': 'Missing comment_id'}, 400
        
    # Get reactions with counts
    reactions = repository.get_comment_reactions(comment_id)
    
    return {'success': True, 'reactions': reactions}


@app.route('/comment/report', methods=['POST'])
@login_required
def comment_report():
    """
    Report a comment as inappropriate
    """
    data = request.get_json()
    comment_id = data.get('comment_id')
    report_type = data.get('report_type')
    content = data.get('content')
    
    if not comment_id or not report_type or not content:
        return {'success': False, 'error': 'Missing required fields'}, 400
        
    if report_type not in ['abusive', 'offensive', 'spam']:
        return {'success': False, 'error': 'Invalid report type'}, 400
        
    # Get current user ID
    user_id = session.get('user_id')
    
    # Create report
    report_id = repository.create_comment_report(comment_id, user_id, report_type, content)
    
    return {'success': True, 'report_id': report_id}


@app.route('/comment/hide', methods=['POST'])
@login_required
def comment_hide():
    """
    Hide a comment (staff only)
    """
    # Check if user is staff
    user_role = session.get('role')
    if user_role not in ['admin', 'editor', 'moderator', 'support_techs']:
        return {'success': False, 'error': 'Permission denied'}, 403
        
    data = request.get_json()
    comment_id = data.get('comment_id')
    
    if not comment_id:
        return {'success': False, 'error': 'Missing comment_id'}, 400
        
    # Hide comment
    repository.hide_comment(comment_id)
    
    return {'success': True}


@app.route('/comment/reports', methods=['GET'])
@login_required
def comment_reports():
    """
    Get reported comments (staff only)
    """
    # Check if user is staff
    user_role = session.get('role')
    if user_role not in ['admin', 'editor', 'moderator', 'support_techs']:
        return {'success': False, 'error': 'Permission denied'}, 403
        
    # Get reports with pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    reports = repository.get_comment_reports(page, per_page)
    
    return {'success': True, 'reports': reports}


@app.route('/comment/report/resolve', methods=['POST'])
@login_required
def comment_report_resolve():
    """
    Resolve a comment report (staff only)
    """
    # Check if user is staff
    user_role = session.get('role')
    if user_role not in ['admin', 'editor', 'moderator', 'support_techs']:
        return {'success': False, 'error': 'Permission denied'}, 403
        
    data = request.get_json()
    report_id = data.get('report_id')
    action = data.get('action')  # 'hide' or 'dismiss'
    
    if not report_id or not action:
        return {'success': False, 'error': 'Missing required fields'}, 400
        
    if action not in ['hide', 'dismiss']:
        return {'success': False, 'error': 'Invalid action'}, 400
        
    # Resolve report
    repository.resolve_comment_report(report_id, action)
    
    return {'success': True}


@app.route('/comment/report/escalate', methods=['POST'])
@login_required
def comment_report_escalate():
    """
    Escalate a comment report to admin team (moderator only)
    """
    # Check if user is moderator
    user_role = session.get('role')
    if user_role != 'moderator':
        return {'success': False, 'error': 'Permission denied'}, 403
        
    data = request.get_json()
    report_id = data.get('report_id')
    reason = data.get('reason')
    
    if not report_id or not reason:
        return {'success': False, 'error': 'Missing required fields'}, 400
        
    # Escalate report
    repository.escalate_comment_report(report_id, reason)
    
    return {'success': True}


@app.route('/comment/reports/page')
@login_required
def comment_reports_page():
    """
    Display the comment reports management page
    """
    # Check if user is staff
    user_role = session.get('role')
    if user_role not in ['admin', 'editor', 'moderator', 'support_techs']:
        flash('您没有权限访问此页面', 'error')
        return redirect(url_for('index'))
        
    # Get page number
    page = request.args.get('page', 1, type=int)
    
    # Get reports
    reports_data = repository.get_comment_reports(page)
    
    return render_template('comment_reports.html',
                         reports=reports_data['reports'],
                         total_pages=reports_data['total_pages'],
                         current_page=page)


