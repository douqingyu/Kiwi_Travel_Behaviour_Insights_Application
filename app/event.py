from app import app, repository
from flask import redirect, render_template, session, url_for, request, flash, jsonify

from app.auth import login_required
from app.error_messages import ErrorMessages
from app.file import allowed_file, upload


@app.route('/event/submit', methods=['GET', 'POST'])
@login_required
def event_submit():
    """
    Add a new event
    """
    data = request.get_json()
    journey_id = data.get('journey_id')
    title = data.get('title')
    description = data.get('description')
    start_datetime = data.get('start_datetime')
    end_datetime = data.get('end_datetime')
    # "2999-12-31 23:59:59" is only a signal, which means users do not enter any end_datetime in this form
    if end_datetime == "":
        end_datetime = "2999-12-31 23:59:59"
    location_name = data.get('location_name')
    photo_urls = data.get('photo_urls', [])

    location_id = repository.get_or_create_location_id(location_name)

    # create event
    event_id = repository.create_event(journey_id, title, description, start_datetime, end_datetime, location_id)
    
    # create event photos
    step = 1
    for photo_url in photo_urls:
        repository.create_event_photo(event_id, photo_url, step)
        step += 1
        
    return {'success': True, "event_id": event_id, "journey_id": journey_id}


@app.route('/event/upload/photo', methods=['POST'])
@login_required
def upload_photo():
    """
    Event photo upload endpoint, only accept png, jpg, jpeg files
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


@app.route('/event/edit', methods=['POST'])
@login_required
def event_edit():
    """
    Edit event
    """
    try:
        data = request.get_json()
        print("Received data:", data)
        print("Request headers:", request.headers) 
        
        if not data:
            return {'success': False, 'message': 'No data received'}, 400
            
        event_id = data.get('id')
        journey_id = data.get('journey_id')
        title = data.get('title')
        description = data.get('description')
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        location_name = data.get('location_name')
        photo_urls = data.get('photo_urls', [])
        is_photo_deleted = data.get('is_photo_deleted', False)
        edit_reason = data.get('edit_reason')
        print("Edit reason:", edit_reason) 

        # Get current user ID and role
        current_user_id = session.get('user_id')
        current_user_role = session.get('role')
        print("Current user role:", current_user_role)

        # Get journey information, check if user is the journey owner
        journey = repository.get_journey_by_id(journey_id)
        if not journey:
            return {'success': False, 'message': ErrorMessages.JOURNEY_NOT_FOUND}, 404

        print("Is journey owner:", str(current_user_id) == str(journey['user_id']))

        # Check if user has permission to edit this event
        is_journey_owner = str(current_user_id) == str(journey['user_id'])
        if not is_journey_owner and current_user_role not in ['admin', 'editor']:
            return {'success': False, 'message': 'You do not have permission to edit this event'}, 403

        # If an administrator or editor edits someone else's event, an edit reason must be provided
        if not is_journey_owner and current_user_role in ['admin', 'editor'] and not edit_reason:
            return {'success': False, 'message': 'Edit reason is required for staff edits'}

        # If user is not the journey owner but is an admin or editor, get the original event information
        if not is_journey_owner and current_user_role in ['admin', 'editor']:
            event = repository.get_event_by_id(event_id)
            if not event:
                return {'success': False, 'message': 'Event not found'}, 404
            # Admins and editors preserve the original date/time
            start_datetime = event['start_datetime']
            end_datetime = event['end_datetime']

            # Allow admins and editors to delete images, but not upload new ones
            if not is_photo_deleted:
                # If the image is not deleted, preserve the original image
                photo_urls = []

        location_id = None
        # add new location
        if location_name:
            location_id = repository.get_or_create_location_id(location_name)

        # Check if there are any content changes
        old_event = repository.get_event_by_id(event_id)

        # update event
        repository.update_event(event_id, title, description, start_datetime, end_datetime, location_id)

        has_content_changes = (
            title != old_event['title'] or
            description != old_event['description'] or
            start_datetime != old_event['start_datetime'] or
            end_datetime != old_event['end_datetime'] or
            location_id != old_event['location_id']
        )

        # Multiple photo processing
        current_photos = repository.get_photos_by_event_id(event_id)
        current_photo_urls = [photo['photo_url'] for photo in current_photos]

        # Check if there are any photo changes
        has_image_changes = False
        if photo_urls or is_photo_deleted:
            has_image_changes = (
                set(photo_urls) != set(current_photo_urls) or
                (is_photo_deleted and current_photos)
            )

        # Record the edit history of content changes
        if has_content_changes:
            changes = []
            edit_contents = []
            if title != old_event['title']:
                changes.append(f"Title changed from '{old_event['title']}' to '{title}'")
                edit_contents.append({
                    'field': 'title',
                    'old': old_event['title'],
                    'new': title
                })
            if description != old_event['description']:
                changes.append(f"Description updated")
                edit_contents.append({
                    'field': 'description',
                    'old': old_event['description'],
                    'new': description
                })
            if start_datetime != old_event['start_datetime']:
                changes.append(f"Start time changed from '{old_event['start_datetime']}' to '{start_datetime}'")
                edit_contents.append({
                    'field': 'start_datetime',
                    'old': old_event['start_datetime'],
                    'new': start_datetime
                })
            if end_datetime != old_event['end_datetime']:
                if end_datetime == "2999-12-31 23:59:59":
                    changes.append("End time removed")
                    edit_contents.append({
                        'field': 'end_datetime',
                        'old': old_event['end_datetime'],
                        'new': None
                    })
                else:
                    changes.append(f"End time changed from '{old_event['end_datetime']}' to '{end_datetime}'")
                    edit_contents.append({
                        'field': 'end_datetime',
                        'old': old_event['end_datetime'],
                        'new': end_datetime
                    })
            if location_id != old_event['location_id']:
                old_location = repository.get_location_by_id(old_event['location_id'])['name']
                new_location = repository.get_location_by_id(location_id)['name']
                changes.append(f"Location changed from '{old_location}' to '{new_location}'")
                edit_contents.append({
                    'field': 'location',
                    'old': old_location,
                    'new': new_location
                })

            # If an administrator or editor edits someone else's event, use the provided edit reason
            if not is_journey_owner and current_user_role in ['admin', 'editor']:
                edit_reason_text = edit_reason
                # Send a system message to the journey owner
                message_content = f"An event in your journey '{journey['title']}' has been edited by {current_user_role}. Reason: {edit_reason}"
                repository.create_message(session.get('user_id'), journey['user_id'], message_content)
            else:
                edit_reason_text = f"Event updated by {'owner' if is_journey_owner else f'staff ({current_user_role})'}: {', '.join(changes)}"

            repository.record_edit_history(None, event_id, current_user_id, 'text', edit_reason_text, edit_contents)

        # Record the edit history of photo changes
        if has_image_changes:
            if is_photo_deleted and not photo_urls:
                repository.record_edit_history(None, event_id, current_user_id, 'image',
                    f"All photos deleted by {'owner' if is_journey_owner else f'staff ({current_user_role})'}")
            elif len(photo_urls) > len(current_photo_urls):
                repository.record_edit_history(None, event_id, current_user_id, 'image',
                    f"Photos added by {'owner' if is_journey_owner else f'staff ({current_user_role})'}")
            elif len(photo_urls) < len(current_photo_urls):
                repository.record_edit_history(None, event_id, current_user_id, 'image',
                    f"Photos removed by {'owner' if is_journey_owner else f'staff ({current_user_role})'}")
            elif set(photo_urls) != set(current_photo_urls):
                repository.record_edit_history(None, event_id, current_user_id, 'image',
                    f"Photos updated by {'owner' if is_journey_owner else f'staff ({current_user_role})'}")

        # Delete the removed photos
        for photo in current_photos:
            if photo['photo_url'] not in photo_urls:
                repository.delete_event_photo_by_id(photo['id'])

        # Add a new photo and set the display_order
        for idx, photo_url in enumerate(photo_urls, start=1):
            if photo_url not in current_photo_urls:
                repository.create_event_photo(event_id, photo_url, idx)
            else:
                # update display_order
                repository.update_event_photo_order(event_id, photo_url, idx)

        return {'success': True, "journey_id": journey_id}
        
    except Exception as e:
        print("Error in event_edit:", str(e)) 
        return {'success': False, 'message': str(e)}, 500

@app.route('/event/delete', methods=['POST'])
@login_required
def event_delete():
    """
    Delete event
    """
    event_id = request.form.get('id')
    journey_id = request.form.get('journey_id')
    
    # get current user id and role
    current_user_id = session.get('user_id')
    current_user_role = session.get('role')
    
    # get journey by journey_id
    journey = repository.get_journey_by_id(journey_id)
    if not journey:
        flash('Journey not found', 'error')
        return redirect(url_for('journeys'))
    
    # authorize the user to delete the event
    if (current_user_id != journey['user_id'] and 
        current_user_role not in ['admin', 'editor']):
        flash('You do not have permission to delete this event', 'error')
        return redirect(url_for('journey_detail', journey_id=journey_id))

    # Delete event photos first
    repository.delete_event_photo(event_id)
    # Then delete the event
    repository.delete_event(event_id)
    
    flash('Event deleted successfully', 'success')
    return redirect(url_for('journey_detail', journey_id=journey_id))

@app.route('/event/like', methods=['POST'])
@login_required
def event_like():
    """
    Like or unlike an event
    """
    data = request.get_json()
    event_id = data.get('event_id')
    
    if not event_id:
        return {'success': False, 'error': 'Missing event_id'}, 400
        
    # Get current user ID
    user_id = session.get('user_id')
    
    # Check if user has already liked this event
    existing_reaction = repository.get_event_reaction(event_id, user_id)
    
    if existing_reaction:
        # Unlike - remove the reaction
        repository.delete_event_reaction(existing_reaction['id'])
        return {'success': True, 'action': 'unliked'}
    else:
        # Like - add new reaction
        repository.create_event_reaction(event_id, user_id)
        return {'success': True, 'action': 'liked'}


@app.route('/event/likes', methods=['GET'])
@login_required
def event_likes():
    """
    Get like count and user's like status for an event
    """
    event_id = request.args.get('event_id')
    
    if not event_id:
        return {'success': False, 'error': 'Missing event_id'}, 400
        
    # Get current user ID
    user_id = session.get('user_id')
    
    # Get like count
    like_count = repository.get_event_like_count(event_id)
    
    # Get user's like status
    user_liked = repository.get_event_reaction(event_id, user_id) is not None
    
    return {
        'success': True,
        'like_count': like_count,
        'user_liked': user_liked
    }

@app.route('/event/detail/<int:event_id>')
@login_required
def event_detail(event_id):
    """
    Get event detail as JSON for modal editing
    """
    event = repository.get_event_by_id(event_id)
    if not event:
        return jsonify({'success': False, 'error': 'Event not found'}), 404

    user_id = session.get('user_id')
    user_liked = repository.get_event_reaction(event_id, user_id) is not None
    like_count = repository.get_event_like_count(event_id)
    location_name = repository.get_location_by_id(event['location_id'])['name']
    comments = repository.get_comments_by_event_id(event_id, user_id)
    comment_count = len(comments)
    photos = repository.get_photos_by_event_id(event_id)
    photo_urls = [photo['photo_url'] for photo in photos]

    return {
        'success': True,
        'location_name': location_name,
        'event': event,
        'photos': photo_urls,
        'user_liked': user_liked,
        'like_count': like_count,
        'comment_count': comment_count
    }

@app.route('/departure_board', methods=['GET', 'POST'])
@login_required
def departure_board():
    if request.method == 'POST':
        tab = request.form.get('tab', 'journey')
        current_page = int(request.form.get('page', 1))
    else:
        tab = request.args.get('tab', 'journey')
        current_page = int(request.args.get('page', 1))
    per_page = 12

    if tab == 'journey':
        events, total, total_pages = repository.get_followed_journeys_events(session['user_id'], current_page, per_page)
    elif tab == 'user':
        events, total, total_pages = repository.get_followed_users_journeys_events(session['user_id'], current_page, per_page)
    elif tab == 'location':
        events, total, total_pages = repository.get_followed_locations_events(session['user_id'], current_page, per_page)
    else:
        return jsonify({'success': False, 'error': 'Invalid tab'}), 400
    
    return render_template('departure_board.html',
                         events=events,
                         total=total,
                         total_pages=total_pages,
                         current_page=current_page,
                         tab=tab)

@app.route('/event/edit/history', methods=['GET'])
@login_required
def get_event_edit_history():
    """
    Get event edit history
    """
    event_id = request.args.get('event_id')
    history = repository.get_event_edit_history(event_id)
    return {'success': True, 'history': history}
    