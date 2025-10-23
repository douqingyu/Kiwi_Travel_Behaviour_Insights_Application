from app import app, repository
from flask import redirect, render_template, session, url_for, request, flash, jsonify
from werkzeug.utils import secure_filename
import os
import uuid

from app.auth import login_required
from app.error_messages import ErrorMessages
from app.file import allowed_file, upload

# Configure file upload
HELP_UPLOAD_FOLDER = 'app/static/file/uploads/help_requests'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

app.config['HELP_UPLOAD_FOLDER'] = HELP_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add status_color filter
@app.template_filter('status_color')
def status_color(status):
    """Convert help request status to Bootstrap color class"""
    status_colors = {
        'new': 'danger',
        'in_progress': 'primary',
        'on_hold': 'warning',
        'resolved': 'success'
    }
    return status_colors.get(status, 'secondary')

@app.route('/helps', methods=['GET', 'POST'], endpoint='helps')
@login_required
def helps():
    """
    Help page, only logged-in users can access this endpoint
    """
    if request.method == 'POST':
        # Handle form submission if needed
        pass

    # Get filter parameters
    user_type = request.args.get('user_type', 'all')
    status = request.args.get('status', 'new')
    assigned_to = request.args.get('assigned_to', None)
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Get user role
    user = repository.get_user_by_id(session['user_id'])
    is_staff = user['role'] in ['admin', 'editor', 'support_techs']

    # Get help requests list
    if is_staff:
        help_requests = repository.get_help_requests_for_staff(
            user_type=user_type,
            page=page,
            per_page=per_page,
            status=status,
            assigned_to=assigned_to
        )
        # Get all staff members list
        staff_members = repository.get_staff_members()
    else:
        help_requests = repository.get_help_requests(
            user_type=user_type,
            page=page,
            per_page=per_page
        )
        staff_members = None

    # Render help center page
    return render_template('helps.html', 
                         help_requests=help_requests['requests'],
                         total_pages=help_requests['total_pages'],
                         current_page=page,
                         user_type=user_type,
                         status=status,
                         assigned_to=assigned_to,
                         staff_members=staff_members,
                         is_staff=is_staff)


@app.route('/help/request', methods=['POST'])
@login_required
def create_help_request():
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')
        
        if not title or not content or not category:
            return jsonify({'error': 'Title, content and category cannot be empty'}), 400
        
        # Handle file uploads
        attachments = []
        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    # make sure there is a dir
                    os.makedirs(app.config['HELP_UPLOAD_FOLDER'], exist_ok=True)
                    file_path = os.path.join(app.config['HELP_UPLOAD_FOLDER'], unique_filename)
                    try:
                        file.save(file_path)
                    except Exception as fe:
                        return jsonify({'error': f'File save error: {str(fe)}'}), 500
                    attachments.append(unique_filename)
                elif file:
                    return jsonify({'error': f'File type not allowed: {file.filename}'}), 400
        
        # Handle bug report specific fields
        bug_data = {}
        if category == 'bug':
            bug_data = {
                'steps': request.form.get('steps'),
                'expected_behavior': request.form.get('expected_behavior'),
                'actual_behavior': request.form.get('actual_behavior')
            }
        
        # Create help request
        request_id = repository.create_help_request(
            user_id=session['user_id'],
            title=title,
            content=content,
            category=category,
            attachments=attachments,
            bug_data=bug_data if category == 'bug' else None
        )
        
        return jsonify({
            'success': True,
            'message': 'Help request submitted successfully',
            'request_number': request_id
        }), 200
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/help/request/<int:request_id>', methods=['GET'])
@login_required
def get_help_request(request_id):
    """
    Get help request details
    """
    help_request = repository.get_help_request_by_id(request_id)
    if not help_request:
        return jsonify({'error': 'Request not found'}), 404
        
    return jsonify(help_request), 200


@app.route('/help/request/<int:request_id>/reply', methods=['POST'])
@login_required
def reply_help_request(request_id):
    """
    Reply to a help request
    """
    content = request.form.get('content')
    if not content:
        return jsonify({'error': 'Reply content cannot be empty'}), 400
        
    # Add reply
    repository.create_help_request_reply(
        request_id=request_id,
        user_id=session['user_id'],
        content=content
    )
    
    # Get request info to send notification
    help_request = repository.get_help_request_by_id(request_id)
    if help_request:
        # If staff replies, automatically update status to in_progress
        user = repository.get_user_by_id(session['user_id'])
        if user['role'] in ['admin', 'editor', 'support_techs']:
            try:
                repository.update_help_request_status(
                    request_id=request_id,
                    status='in_progress'
                )
            except ValueError:
                # If status is already in_progress, ignore error
                pass
    
    return jsonify({'message': 'Reply submitted successfully'}), 200


@app.route('/help/request/<int:request_id>/assign', methods=['POST'])
@login_required
def assign_help_request(request_id):
    """
    Assign help request to staff member
    """
    staff_id = request.form.get('staff_id')
    if not staff_id:
        return jsonify({'error': 'Please select a staff member'}), 400

    # Assign request
    repository.assign_help_request(request_id, staff_id)
    return jsonify({'message': 'Request assigned successfully'}), 200


@app.route('/help/request/<int:request_id>/abandon', methods=['POST'])
@login_required
def abandon_help_request(request_id):
    """
    Abandon handling a help request
    """
    repository.abandon_help_request(request_id)
    return jsonify({'message': 'Request abandoned successfully'}), 200


@app.route('/help/request/<int:request_id>/status', methods=['POST'])
@login_required
def update_help_request_status(request_id):
    """
    Update help request status
    """
    status = request.form.get('status') 
    hold_reason = request.form.get('hold_reason') 
    resolution_summary = request.form.get('resolution_summary') 
    
    if not status:
        return jsonify({'error': 'Status is required'}), 400

    try:
        repository.update_help_request_status(
            request_id=request_id,
            status=status,
            hold_reason=hold_reason,
            resolution_summary=resolution_summary
        )
        return jsonify({'message': 'Status updated successfully'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error updating status'}), 500


@app.route('/my-help-requests')
@login_required
def my_help_requests():
    """User view their submitted help request history"""
    # Get filter parameters
    status = request.args.get('status', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    # Get help requests list
    result = repository.get_user_help_requests(
        user_id=session['user_id'],
        status=status,
        page=page,
        per_page=per_page
    )

    # Debug print
    print(f"Debug - Help requests result: {result}")

    # Ensure we have valid data
    if not result:
        result = {'requests': [], 'total_pages': 0}

    return render_template(
        'my_help_requests.html',
        help_requests=result.get('requests', []),
        total_pages=result.get('total_pages', 0),
        current_page=page,
        status=status
    )

@app.route('/help/request/<int:request_id>/reopen', methods=['POST'])
@login_required
def reopen_help_request(request_id):
    """
    Reopen a resolved help request
    """
    # Get request info
    help_request = repository.get_help_request_by_id(request_id)
    if not help_request:
        return jsonify({'error': 'Request not found'}), 404

    # Check if user is the owner
    if help_request['user_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized to perform this action'}), 403

    # Check if request is resolved
    if help_request['status'] != 'resolved':
        return jsonify({'error': 'Can only reopen resolved requests'}), 400

    # Update request status to new
    try:
        repository.update_help_request_status(
            request_id=request_id,
            status='new'
        )
        return jsonify({'message': 'Request reopened successfully'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Error updating status'}), 500
