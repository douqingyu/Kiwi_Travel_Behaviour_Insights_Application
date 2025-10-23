from app import app, repository
from flask import redirect, render_template, session, url_for, request, flash, jsonify

from app.auth import login_required
from app.error_messages import ErrorMessages
from app.file import allowed_file, upload

def get_unread_messages_count(user_id):
    """Get the number of unread messages for the user"""
    query = """
    SELECT COUNT(*) as count 
    FROM private_messages 
    WHERE receiver_id = %s AND is_read = FALSE
    """
    result = repository.db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0

@app.route('/messages', methods=['GET'])
@login_required
def messages():
    conversations = repository.get_conversations(session['user_id'])
    unread_count = get_unread_messages_count(session['user_id'])
    
    # Get the user ID to start a conversation with
    target_user_id = request.args.get('user_id')
    if target_user_id:
        # Check if the target user exists
        target_user = repository.get_user_by_id(target_user_id)
        if not target_user:
            flash('User not found', 'error')
            return redirect(url_for('messages'))
            
        # Check if there is already a conversation with this user
        existing_conversation = None
        for conv in conversations:
            if str(conv['other_user_id']) == str(target_user_id):
                existing_conversation = conv
                break
                
        if existing_conversation:
            # If a conversation already exists, redirect to that conversation
            return render_template('message.html', 
                                conversations=conversations,
                                unread_messages_count=unread_count,
                                selected_conversation_id=target_user_id)
    
    return render_template('message.html', 
                         conversations=conversations,
                         unread_messages_count=unread_count)

@app.route('/messages/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    # get message
    messages = repository.get_messages_by_conversation(conversation_id, session['user_id'])
    
    # Mark all unread messages as read.
    for message in messages:
        if not message['is_read'] and message['receiver_id'] == session['user_id']:
            repository.mark_message_read(message['id'], session['user_id'])
    
    return {
        'success': True,
        'messages': messages
    }

@app.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    
    if not receiver_id or not content:
        return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
    # Check if the user has permission to send messages
    user = repository.get_user_by_id(session['user_id'])
    if not repository.can_send_message(user):
        return {'success': False, 'message': 'You need an active subscription to send messages'}, 403
        
    message_id = repository.create_message(session['user_id'], receiver_id, content)
    return jsonify({'success': True, 'message_id': message_id}), 201

@app.route('/messages/read/<int:message_id>', methods=['PUT'])
@login_required
def mark_message_read(message_id):
    repository.mark_message_read(message_id, session['user_id'])
    return jsonify({'success': True})





