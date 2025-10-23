from app import app
from app import repository
from app.auth import login_required, role_required, session_blacklist, force_logout
from app.enums.user_status_enum import UserStatus
from app.error_messages import ErrorMessages
from flask import redirect, render_template, request, session, url_for, flash, jsonify

from app.enums.role_enum import Role


@app.route('/admin/user/management', methods=['GET', 'POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def user_management():
    """
    User management page. Only admin can access this endpoint, admin can filter users by status, role and keyword
    Keyword is user's first_name or last_name，
    """
    # get filter parameters
    status = request.form.get('status', None)  # active/banned
    role = request.form.get('role', None)  # admin/editor/traveller
    keyword = request.form.get('keyword', None)  # search by first_name / last_name
    search_type = request.form.get('search_type', None)  # first_name / last_name / username / email
    can_share = request.form.get('can_share', None)  # 1/0 for can share/cannot share
    current_page = int(request.form.get('page', 1))  # page number, default 1
    per_page = 12  # default 12

    # get data
    users, total, total_pages = repository.get_user_page(status, role, keyword, current_page, per_page, search_type, can_share)

    # Get the current subscription information for each user
    for user in users:
        user['current_subscription'] = repository.get_current_subscription(user['id'])

    return render_template('user_management.html', users=users, current_page=current_page, total=total,
                           total_pages=total_pages, role=role, status=status, keyword=keyword, search_type=search_type,
                           can_share=can_share)

@app.route('/admin/edit/user', methods=['POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def admin_edit_user():
    """
    Edit user role and status, only admin can access this endpoint
    """
    # get data from request
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'message': 'Invalid request data'
        }), 400

    user_id = data.get('user_id')
    role = data.get('role')
    status = data.get('status')
    can_share = data.get('can_share', False)

    # verify request avaliable
    if not all([user_id, role, status]):
        return jsonify({
            'success': False,
            'message': 'Missing required fields'
        }), 400

    # verify role
    if not Role.from_value(role):
        return jsonify({
            'success': False,
            'message': ErrorMessages.INVALID_ROLE
        }), 400
    
    # verify status
    if not UserStatus.from_value(status):
        return jsonify({
            'success': False,
            'message': ErrorMessages.INVALID_STATUS
        }), 400

    # verify if selected user exists
    user = repository.get_user_by_id(user_id)
    if not user:
        return jsonify({
            'success': False,
            'message': ErrorMessages.ACCOUNT_NOT_FOUND
        }), 404

    try:
        # Get the original role
        original_role = user['role']
        
        # update user role and status
        repository.update_user_role(user_id, role)
        repository.update_user_status(user_id, status)
        repository.update_user_can_share(user_id, can_share)

        # If the role changes, send a notification
        if original_role != role:
            notification_content = f"Your role has been changed from {original_role} to {role}."
            repository.create_message(session['user_id'], user_id, notification_content)

        # force logout
        force_logout(int(user_id))

        return jsonify({
            'success': True,
            'message': ErrorMessages.USER_UPDATED_SUCCESSFULLY
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/admin/edit/history', methods=['GET', 'POST'])
@login_required
@role_required(Role.ADMIN.value)
def edit_history():
    """
    Edit history management page. Only administrators and support technicians can access this page.
    Filtering by editor, edit type, and keywords is supported.
    """
    # Get the filter parameters
    editor_id = request.form.get('editor_id', None)
    edit_type = request.form.get('edit_type', None)
    current_page = int(request.form.get('page', 1))
    per_page = 10

    # Get the data
    edit_history, total, total_pages = repository.get_all_edit_history(
        page=current_page,
        per_page=per_page,
        editor_id=editor_id,
        edit_type=edit_type
    )

    # Get the list of all editors (for filtering)
    staff_members = repository.get_staff_members()

    return render_template('edit_history.html',
                         edit_history=edit_history,
                         current_page=current_page,
                         total=total,
                         total_pages=total_pages,
                         editor_id=editor_id,
                         edit_type=edit_type,
                         staff_members=staff_members)