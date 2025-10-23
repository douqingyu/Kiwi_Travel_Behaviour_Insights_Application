from app import app, repository
from flask import redirect, render_template, session, url_for, request, flash, jsonify
from datetime import datetime, date

from app.auth import login_required, role_required
from app.enums.role_enum import Role
from app.error_messages import ErrorMessages
from app.file import allowed_file, upload


@app.route('/journeys', methods=['GET', 'POST'])
@login_required
def journeys():
    """
    Journeys page, user can filter journeys by status, and view all journeys
    """
    if request.method == 'POST':
        tab = request.form.get('tab', 'my')
    else:
        tab = request.args.get('tab', 'my')
        
    search_type = request.form.get('searchType', 'keyword')
    search_input = request.form.get('searchInput')
    current_page = int(request.form.get('page', 1))  # page number, default 1
    per_page = 12  # default 12

    # verify current user's role
    if tab == 'hidden' and session.get('role') not in [Role.ADMIN.value, Role.SUPPORT_TECHS.value, Role.EDITOR.value]:
        flash('You do not have permission to view hidden journeys', 'error')
        return redirect(url_for('journeys', tab='my', search_type=search_type, search_input=search_input))

    # update has_active_subscription in session
    has_active_subscription = repository.is_premiun_user(session.get("user_id"))
    session.update({
        'has_active_subscription': has_active_subscription,
    })
    
    user_id = None
    is_public = None
    is_hidden = None
    if tab == 'my':
        user_id = session.get("user_id")
    elif tab == 'public':
        is_public = True
        is_hidden = False
    elif tab == 'hidden':
        is_hidden = True

    # search journey by keyword or location
    keyword = None
    location_ids = []
    if search_input:
        if search_type == 'keyword':
            keyword = search_input
        elif search_type == 'location':
            # get location_id by location_name
            locations = repository.get_locations_like_name(search_input)
            if locations:
                location_ids = [location['id'] for location in locations]
            else:
                location_ids = [0]

    # Get user id
    current_user_id = session.get('user_id')
    journeys, total, total_pages = repository.get_journeys_page(current_user_id, current_page, per_page, is_public, is_hidden, keyword, location_ids, tab)

    return render_template('journeys.html', 
                         journeys=journeys, 
                         tab=tab, 
                         current_page=current_page, 
                         total=total,
                         total_pages=total_pages, 
                         search_type=search_type,
                         search_input=search_input)


@app.route('/journey/submit', methods=['POST'])
@login_required
def journey_submit():
    """
    Submit a new journeys
    """
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    is_public = data.get('is_public', False)
    is_published = data.get('is_published', False)
    start_date = data.get('start_date')

    # validate title and description
    if not title or not description:
        return {'success': False, 'message': ErrorMessages.TITLE_DESCRIPTION_START_DATE_REQUIRED}

    user_id = session['user_id']
    #save journey
    journey_id = repository.create_journey(user_id, title, description, is_public, is_published, start_date)
    return {'success': True, "journey_id": journey_id}

@app.route('/journey/list', methods=['POST'])
@login_required
def get_journeys():
    """
    Get all journeys
    """
    user_id = session.get("user_id")
    role = session.get("role")
    event_id = request.json.get("event_id")
    
    # if user is admin or editor, and event_id is provided, return the journey of the event
    if role in ['admin', 'editor'] and event_id:
        event = repository.get_event_by_id(event_id)
        journey = repository.get_journey_by_id(event['journey_id'])
        return {'success': True, "journeys": [journey] if journey else []}
    
    # otherwise, return all journeys of the user
    journeys = repository.get_journeys(user_id)
    return {'success': True, "journeys": journeys}


@app.route('/journey/detail/<int:journey_id>', methods=['GET'])
@login_required
def journey_detail(journey_id):
    """
    Journey detail page
    """
    # get the tab parameter from request
    tab = request.args.get('tab', 'my')
    
    # check if journey exists
    journey = repository.get_journey_by_id(journey_id)
    if not journey:
        flash(ErrorMessages.JOURNEY_NOT_FOUND, "error")
        return redirect(url_for('journeys'))
        
    # get all events
    events = repository.get_events_by_journey_id(journey_id)

    # get author information
    author = repository.get_user_by_id(journey['user_id'])
    # add profile of owner to journey
    journey['first_name'] = author['first_name']
    journey['last_name'] = author['last_name']
    journey['profile_image'] = author['profile_image']

    # Get current user ID
    user_id = session.get('user_id')
    
    # Get like status and comment count for each event
    for event in events:
        event['user_liked'] = repository.get_event_reaction(event['id'], user_id) is not None
        event['like_count'] = repository.get_event_like_count(event['id'])
        comments = repository.get_comments_by_event_id(event['id'], user_id)
        event['comment_count'] = len(comments)

    return render_template('journey_detail.html', 
                         journey=journey, 
                         events=events, 
                         author=author, 
                         tab=tab)


@app.route('/journey/update/public', methods=['POST'])
@login_required
def update_journey_public():
    """
    Update journey public
    """
    journey_id = request.form.get('journey_id')
    is_public = request.form.get('is_public')
    tab = request.form.get('tab', 'my')
    journey = repository.get_journey_by_id(journey_id)

    # can not find a journey by selected journey id
    if not journey:
        flash(ErrorMessages.JOURNEY_NOT_FOUND, "error")
    # update selected journey status
    else:
        repository.update_journey_public(journey_id, is_public)
    return redirect(url_for('journey_detail', journey_id=journey_id, tab=tab))

@app.route('/journey/update/published', methods=['POST'])
@login_required
def update_journey_published():
    """
    Update journey published
    """
    journey_id = request.form.get('journey_id')
    is_published = request.form.get('is_published')
    tab = request.form.get('tab', 'my')
    journey = repository.get_journey_by_id(journey_id)

    # can not find a journey by selected journey id
    if not journey:
        flash(ErrorMessages.JOURNEY_NOT_FOUND, "error")
    # update selected journey status
    else:
        repository.update_journey_published(journey_id, is_published)
    return redirect(url_for('journey_detail', journey_id=journey_id, tab=tab))

@app.route('/journey/update/no_edit', methods=['POST'])
@login_required
def update_journey_no_edit():
    """
    Update journey no_edit status
    """
    journey_id = request.form.get('journey_id')
    no_edit = request.form.get('no_edit') == 'true'  # Change to boolean
    tab = request.form.get('tab', 'my')
    journey = repository.get_journey_by_id(journey_id)

    # can not find a journey by selected journey id
    if not journey:
        flash(ErrorMessages.JOURNEY_NOT_FOUND, "error")
    # update selected journey status
    else:
        # varify is user have right to update their journeys to no_edit
        user_id = session.get('user_id')
        role = session.get('role')
        has_active_subscription = session.get('has_active_subscription')
        
        if str(user_id) == str(journey['user_id']) and (has_active_subscription or role in ['admin', 'editor', 'support_techs']):
            repository.update_journey_no_edit(journey_id, no_edit)
        else:
            flash('You do not have permission to set no_edit status', 'error')
            
    return redirect(url_for('journey_detail', journey_id=journey_id, tab=tab))

@app.route('/journey/update/hidden', methods=['POST'])
@login_required
@role_required(Role.EDITOR.value, Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def update_journey_hidden():
    """
    Update journey hidden
    """
    journey_id = request.form.get('journey_id')
    is_hidden = request.form.get('is_hidden')
    tab = request.form.get('tab', 'hidden')
    journey = repository.get_journey_by_id(journey_id)

    # can not find a journey by selected journey id
    if not journey:
        flash(ErrorMessages.JOURNEY_NOT_FOUND, "error")
    # update selected journey status
    else:
        repository.update_journey_hidden(journey_id, is_hidden)
    return redirect(url_for('journeys', tab=tab))

@app.route('/journey/upload/photo', methods=['POST'])
@login_required
def upload_journey_photo():
    """
    Journey photo upload endpoint, only accept png, jpg, jpeg files
    """
    try:
        if 'file' not in request.files:
            return {'success': False, 'error': 'No file uploaded'}, 400

        file = request.files['file']
        if file.filename == '':
            return {'success': False, 'error': 'No file selected'}, 400

        # validate file type, only jpg, jpeg, and png are allowed here
        if not allowed_file(file.filename):
            return {'success': False, 'error': ErrorMessages.INVALID_FILE_TYPE}, 400

        # save selected photo
        filename = upload(file, prefix='photo')
        return {'success': True, 'filename': filename}
    except Exception as e:
        return {'success': False, 'error': str(e)}, 500

@app.route('/journey/update', methods=['POST'])
@login_required
def update_journey():
    """
    Update journey
    """
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    start_date = data.get('start_date')
    journey_id = data.get('journey_id')
    photo_url = data.get('photo_url')
    is_photo_deleted = data.get('is_photo_deleted', False)
    edit_reason = data.get('edit_reason')

    # validate title and description
    if not title or not description:
        return {'success': False, 'message': ErrorMessages.TITLE_DESCRIPTION_START_DATE_REQUIRED}

    journey = repository.get_journey_by_id(journey_id)
    # can not find a journey by selected journey id
    if not journey:
        return {'success': False, 'message': ErrorMessages.JOURNEY_NOT_FOUND}
    
    # Get current user ID and role
    current_user_id = session.get('user_id')
    current_user_role = session.get('role')
    
    # Check if user has permission to edit this journey
    is_journey_owner = str(current_user_id) == str(journey['user_id'])
    if not is_journey_owner and current_user_role not in ['admin', 'editor']:
        return {'success': False, 'message': ErrorMessages.UNAUTHORIZED_ACTION}

    # reason is needed if administrator or editor want to edit others' journeys
    if not is_journey_owner and current_user_role in ['admin', 'editor'] and not edit_reason:
        return {'success': False, 'message': 'Edit reason is required for staff edits'}

    # varify any details were edited
    old_date = to_date(journey['start_date'])
    new_date = to_date(start_date)
    date_changed = (old_date != new_date) if (old_date and new_date) else False
    has_content_changes = (
        title != journey['title'] or 
        description != journey['description'] or 
        date_changed
    )
    
    # varify if images were edited
    has_image_changes = False
    if photo_url or is_photo_deleted:
        covers = repository.get_covers_by_journey_id(journey_id)
        has_image_changes = (
            (photo_url and (not covers or covers[0]['photo_url'] != photo_url)) or
            (is_photo_deleted and covers)
        )

    # save journey
    repository.update_journey(journey_id, title, description, start_date)

    # Handle image updates
    covers = repository.get_covers_by_journey_id(journey_id)
    
    # If admin or editor and image deletion requested, delete the image
    if not is_journey_owner and current_user_role in ['admin', 'editor'] and is_photo_deleted:
        if covers:
            repository.delete_journey_cover(journey_id)
            if has_image_changes:
                repository.record_edit_history(journey_id, None, current_user_id, 'image', edit_reason or f"Cover image deleted by {current_user_role}")
    # Only journey owners can upload images or fully control images
    elif is_journey_owner:
        # if the selected journey has a cover in the database already, replace it with the new cover if the URLs are different
        if photo_url:
            if covers and covers[0]['photo_url'] != photo_url:
                repository.update_journey_cover(covers[0]['id'], photo_url)
                if has_image_changes:
                    repository.record_edit_history(journey_id, None, current_user_id, 'image', "Cover image updated by owner")
            elif not covers:
                repository.create_journey_cover(journey_id, photo_url)
                if has_image_changes:
                    repository.record_edit_history(journey_id, None, current_user_id, 'image', "Cover image added by owner")
        elif covers:
            repository.delete_journey_cover(journey_id)
            if has_image_changes:
                repository.record_edit_history(journey_id, None, current_user_id, 'image', "Cover image deleted by owner")

    # save edit details
    if has_content_changes:
        changes = []
        edit_contents = []
        if title != journey['title']:
            changes.append(f"Title changed from '{journey['title']}' to '{title}'")
            edit_contents.append({
                'field': 'title',
                'old': journey['title'],
                'new': title
            })
        if description != journey['description']:
            changes.append(f"Description updated")
            edit_contents.append({
                'field': 'description',
                'old': journey['description'],
                'new': description
            })
        if date_changed:
            changes.append(f"Start date changed from '{old_date}' to '{new_date}'")
            edit_contents.append({
                'field': 'start_date',
                'old': old_date.strftime('%Y-%m-%d') if old_date else '',
                'new': new_date.strftime('%Y-%m-%d') if new_date else ''
            })
        
        # reason is needed if administrator or editor want to edit others' journeys
        if not is_journey_owner and current_user_role in ['admin', 'editor']:
            edit_reason_text = edit_reason
            # send message about this edit to journey owner
            message_content = f"Your journey '{journey['title']}' has been edited by {current_user_role}. Reason: {edit_reason}"
            repository.create_message(session.get('user_id'), journey['user_id'], message_content)
        else:
            edit_reason_text = f"Journey updated by {'owner' if is_journey_owner else f'staff ({current_user_role})'}: {', '.join(changes)}"
        
        for content in edit_contents:
            if isinstance(content['old'], (datetime, date)):
                content['old'] = content['old'].strftime('%Y-%m-%d')
            if isinstance(content['new'], (datetime, date)):
                content['new'] = content['new'].strftime('%Y-%m-%d')
        
        repository.record_edit_history(journey_id, None, current_user_id, 'text', edit_reason_text, edit_contents)

    return {'success': True, "journey_id": journey_id}


@app.route('/journey/', methods=['POST'])
@login_required
def delete_journey():
    """
    Delete journey
    """
    journey_id = request.form.get('journey_id')
    tab = request.form.get('tab', 'my')
    journey = repository.get_journey_by_id(journey_id)

    # can not find a journey by selected journey id
    if not journey:
        flash(ErrorMessages.JOURNEY_NOT_FOUND, "error")
    else:
        repository.delete_journey(journey_id)
    flash(ErrorMessages.JOURNEY_DELETED, "success")
    return redirect(url_for('journeys', tab=tab))

@app.route('/journeys/published', methods=['GET'])
def publishedjourneys():
    """
    Users could get all published journeys without login 
    """
    per_page = 12
    current_page = request.args.get("current_page")


    journeys, total, total_pages = repository.get_published_journeys_page( current_page, per_page, False)

    return render_template('journeys.html', 
                         journeys=journeys, 
                         current_page=current_page, 
                         total=total,
                         total_pages=total_pages, 
                         )

@app.route('/journey/follow', methods=['POST'])
@login_required
def toggle_journey_follow():
    """
    follow/unfollow journey
    """
    journey_id = request.form.get('journey_id')
    user_id = session.get('user_id')
    
    # varify if journey exists
    journey = repository.get_journey_by_id(journey_id)
    if not journey:
        return {'success': False, 'message': ErrorMessages.JOURNEY_NOT_FOUND}
    
    # follow/unfollow
    is_following = repository.toggle_journey_follow(journey_id, user_id)
    
    return {
        'success': True,
        'is_following': is_following
    }


@app.route('/api/departures/location', methods=['GET'])
@login_required
def get_location_departures():
    """
    get journey list which followed by location
    """
    current_page = int(request.args.get('page', 1))
    per_page = 5 
    
    journeys, total, total_pages = repository.get_followed_locations_journeys(
        session.get('user_id'),
        current_page,
        per_page
    )
    
    return {
        'success': True,
        'journeys': journeys,
        'total': total,
        'total_pages': total_pages,
        'current_page': current_page
    }


@app.route('/journey/edit/history', methods=['GET'])
@login_required
def get_journey_edit_history():
    """
    Get journey edit history
    """
    journey_id = request.args.get('journey_id')
    history = repository.get_journey_edit_history(journey_id)
    return {'success': True, 'history': history}

@app.route('/journey/appeal', methods=['POST'])
@login_required
def create_journey_appeal():
    """
    创建旅程申诉
    """
    journey_id = request.form.get('journey_id')
    content = request.form.get('content')
    
    if not content:
        return jsonify({'success': False, 'message': 'Please provide appeal content'}), 400
    
    # varify if journey is hidden
    journey = repository.get_journey_by_id(journey_id)
    if not journey:
        return jsonify({'success': False, 'message': 'Journey not found'}), 404
    
    if not journey['is_hidden']:
        return jsonify({'success': False, 'message': 'This journey is not hidden'}), 400
    
    # crate appeal
    repository.create_appeal(
        session.get('user_id'),
        'hidden_journey',
        content,
        journey_id=journey_id
    )
    
    return jsonify({'success': True, 'message': 'Your appeal has been submitted successfully'})

@app.route('/appeals', methods=['GET'])
@login_required
@role_required(Role.ADMIN.value, Role.EDITOR.value)
def appeals():
    """
    appeal list page
    """
    page = int(request.args.get('page', 1))
    status = request.args.get('status')
    per_page = 10
    
    # if status is 'all' or 'None'，get all appeals
    if status == 'all':
        status = None
    
    appeals, total = repository.get_appeals(page, per_page, status)
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('appeals.html',
                         appeals=appeals,
                         current_page=page,
                         total_pages=total_pages,
                         status=status)

@app.route('/appeal/<int:appeal_id>', methods=['GET'])
@login_required
@role_required(Role.ADMIN.value, Role.EDITOR.value)
def appeal_detail(appeal_id):
    """
    appeal detail page
    """
    appeal = repository.get_appeal_by_id(appeal_id)
    if not appeal:
        flash('Appeal not found', 'error')
        return redirect(url_for('appeals'))
    
    return render_template('appeal_detail.html', appeal=appeal)

@app.route('/appeal/<int:appeal_id>/resolve', methods=['POST'])
@login_required
@role_required(Role.ADMIN.value, Role.EDITOR.value)
def resolve_appeal(appeal_id):
    """
    approve/reject appeal
    """
    action = request.form.get('action')
    if action not in ['approve', 'reject']:
        flash('Invalid action', 'error')
        return redirect(url_for('appeal_detail', appeal_id=appeal_id))
    
    appeal = repository.get_appeal_by_id(appeal_id)
    if not appeal:
        flash('Appeal not found', 'error')
        return redirect(url_for('appeals'))
    
    if appeal['status'] != 'pending':
        flash('This appeal has already been processed', 'error')
        return redirect(url_for('appeal_detail', appeal_id=appeal_id))
    
    # update appeal status
    repository.update_appeal_status(appeal_id, 'resolved')
    
    # If journey status is hidden and administrator approve thisc appeal, this journey will be unhidden
    if appeal['appeal_type'] == 'hidden_journey' and action == 'approve':
        journey = repository.get_journey_by_id(appeal['journey_id'])
        if journey:
            repository.update_journey_hidden(journey['id'], False)
            flash('Journey has been unhidden', 'success')
    
    flash('Appeal has been processed successfully', 'success')
    return redirect(url_for('appeals'))

def to_date(val):
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return datetime.strptime(val, '%Y-%m-%d').date()
        except Exception:
            try:
                return datetime.strptime(val, '%Y-%m-%d %H:%M:%S').date()
            except Exception:
                return None
    return None