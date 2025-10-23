import io
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from flask import current_app, render_template, session, request, redirect, url_for, flash, jsonify, send_file
from app import app
from app import repository
from app import app
from app import repository
from flask import redirect, render_template, session, url_for, request, flash
from datetime import datetime, timedelta
from decimal import Decimal


from app.auth import login_required, role_required
from app.enums.role_enum import Role
from app.error_messages import ErrorMessages
from app.utils.pdf_generator import generate_subscription_pdf


@app.route('/subscriptions', methods=['GET'])
@login_required
def subscriptions():
    """Subscription page, where users can view all available subscription plans"""
    # Get all available subscription plans
    plans = repository.get_subscription_plans()
    
    # Get the user's current subscription information
    user_id = session.get('user_id')
    current_subscription = repository.get_current_subscription(user_id)
    
    # Check if a free trial can be started
    can_start_trial = repository.can_start_free_trial(user_id)
    
    # Get the list of features for the subscription plan
    features = []
    if current_subscription:
        features = get_subscription_features(current_subscription['plan_id'])['features']
    
    # Get the user's country information.
    billing_country = 'NZ'  # default NZ
    
    return render_template('subscriptions.html',
                         plans=plans,
                         current_subscription=current_subscription,
                         can_start_trial=can_start_trial,
                         features=features,
                         billing_country=billing_country,
                         now=datetime.now())

@app.route('/subscription/start-trial', methods=['POST'])
@login_required
def start_free_trial():
    """start free trail"""
    user_id = session.get('user_id')
    
    if not repository.can_start_free_trial(user_id):
        flash('You have already used the free trial.', 'error')
        return redirect(url_for('subscriptions'))
    
    # get free trial
    plan = repository.get_free_trial_plan()
    if not plan:
        flash('System error: free trial plan not found', 'error')
        return redirect(url_for('subscriptions'))
    
    # Create subscription record
    start_date = datetime.now()
    end_date = start_date + timedelta(days=30)  # free for 30 days
    
    repository.create_subscription(
        user_id=user_id,
        plan_id=plan['id'],
        start_date=start_date,
        end_date=end_date,
        payment_amount=0,
        gst_amount=0,
        billing_country='NZ',
        is_free_trial=True
    )
    
    flash('The free trial has started and is valid for 30 days', 'success')
    return redirect(url_for('subscriptions'))

@app.route('/subscription/upgrade', methods=['POST'])
@login_required
def upgrade_subscription():
    """Upgrade subscription plan"""
    user_id = session.get('user_id')
    plan_id = request.form.get('plan_id')
    billing_country = request.form.get('billing_country', 'NZ')
    
    # Get plan information
    plan = repository.get_subscription_plan(plan_id)
    if not plan:
        flash('Invalid subscription plan', 'error')
        return redirect(url_for('subscriptions'))
    
    # get current subscription
    current_sub = repository.get_current_subscription(user_id)
    start_date = datetime.now()
    
    # If there is an existing subscription, extend the end date
    if current_sub:
        end_date = current_sub['end_date'] + timedelta(days=30 * plan['months'])
    else:
        end_date = start_date + timedelta(days=30 * plan['months'])
    
    # get price
    price = plan['price_nz'] if billing_country == 'NZ' else plan['price_other']
    if plan['discount']:
        price = price * (1 - plan['discount'] / 100)
    gst_amount = price * 0.15 if billing_country == 'NZ' else 0
    
    # Create a new subscription record
    repository.create_subscription(
        user_id=user_id,
        plan_id=plan_id,
        start_date=start_date,
        end_date=end_date,
        payment_amount=price,
        gst_amount=gst_amount,
        billing_country=billing_country,
        is_free_trial=False
    )
    
    flash('Subscription upgraded successfully', 'success')
    return redirect(url_for('subscriptions'))

@app.route('/subscription/features/<int:plan_id>', methods=['GET'])
@login_required
def get_subscription_features(plan_id):
    """Get the list of features for the subscription plan"""
    features = {
        1: [  # Free Trial
            "Basic access to all features",
            "Email support",
            "Community access"
        ],
        2: [  # One Month
            "All Free Trial features",
            "Priority support",
            "Advanced analytics"
        ],
        3: [  # One Quarter
            "All One Month features",
            "Custom reports",
            "API access"
        ],
        4: [  # One Year
            "All One Quarter features",
            "Dedicated support",
            "Custom integrations"
        ]
    }
    return {'success': True, 'features': features.get(plan_id, [])}

@app.route('/subscription/check-expiry', methods=['GET'])
@login_required
def check_subscription_expiry():
    """Check if the subscription is about to expire"""
    user_id = session.get('user_id')
    current_sub = repository.get_current_subscription(user_id)
    
    if not current_sub:
        return {'success': True, 'expiry_info': None}
    
    days_remaining = (current_sub['end_date'] - datetime.now()).days
    if days_remaining <= 7:
        return {
            'success': True,
            'expiry_info': {
                'plan_name': current_sub['plan_name'],
                'days_remaining': days_remaining,
                'is_free_trial': current_sub['is_free_trial']
            }
        }
    return {'success': True, 'expiry_info': None} 

@app.route('/subscription/payment/failed', methods=['GET'])
@login_required
def subscription_payment_failed():
    """
    Failed to pay a bill for subscription
    This API is just for front-end test
    """
    return {'success': False}

@app.route('/subscription/payment', methods=['POST'])
@login_required
def subscription_payment():
    """
    According to the latest subscription and selected plan, create a new record
    """
    try:
        data = request.get_json()
        plan_id = data.get('plan_id')
        billing_country = data.get('billing_country')
        is_free_trial = data.get('is_free_trial')
        granted_by_admin = data.get('granted_by_admin')
        payment_info = data.get('payment_info')

        if not plan_id:
            return jsonify({"success": False, "error_message": "Missing required parameters"})

        user_id = session.get('user_id')
        role = session.get('role')
        
        # Get plan information
        plan = repository.get_plan_by_id(plan_id)
        if not plan:
            return jsonify({"success": False, "error_message": "Invalid subscription plan"})
        
        # Get the latest subscription information
        latest_subscription = repository.get_latest_subscription_by_id(user_id)
        
        # Set start date
        start_date = datetime.now()
        if latest_subscription and latest_subscription['end_date'] > datetime.now():
            start_date = latest_subscription['end_date']
        
        # Set end date 
        months =plan.get('months', 1) 
        # Get end date
        year = start_date.year + (start_date.month + months - 1) // 12
        month = (start_date.month + months - 1) % 12 + 1
        day = min(start_date.day, [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
        end_date = datetime(year, month, day, start_date.hour, start_date.minute, start_date.second)
        
        # get price
        if is_free_trial or granted_by_admin or role in ['admin', 'editor']:
            payment_amount = Decimal('0.00')
            gst_amount = Decimal('0.00')
        else:
            if billing_country == 'NZ':
                base_price = plan['price_nz']
            else:
                base_price = plan['price_other']
            
            # get discount
            if plan['discount']:
                payment_amount = base_price * (1 - Decimal(str(plan['discount'])) / 100)
            else:
                payment_amount = base_price
                
            # get GST
            if billing_country == 'NZ':
                gst_amount = payment_amount * Decimal('0.15')  # 15% GST
            else:
                gst_amount = Decimal('0.00')

        # Create a subscription record
        subscription_id = repository.create_subscription(
            user_id=user_id,
            plan_id=plan_id,
            start_date=start_date,
            end_date=end_date,
            payment_amount=payment_amount,
            gst_amount=gst_amount,
            billing_country=billing_country,
            is_free_trial=is_free_trial,
            granted_by_admin=granted_by_admin or role in ['admin', 'editor']
        )

        if not subscription_id:
            return jsonify({"success": False, "error_message": "Failed to create subscription"})

        # Get the newly created subscription information
        new_subscription = repository.get_subscription_by_id(subscription_id)
        if not new_subscription:
            return jsonify({"success": False, "error_message": "Failed to retrieve subscription details"})

        # Update session
        update_session_after_subscription(new_subscription)

        # Update user's journey publish function
        repository.update_user_can_publish(user_id, True)

        return jsonify({
            'success': True, 
            "subscription_id": subscription_id,
            "subscription": new_subscription
        })
    except Exception as e:
        current_app.logger.error(f"Error in subscription_payment: {str(e)}")
        return jsonify({"success": False, "error_message": "An unexpected error occurred"})

def update_session_after_subscription(subscription):
    """Update subscription information in the session"""
    if not subscription:
        return

    session.update({
        'loggedin': True,
        'user_id': session.get("user_id"),
        'username': session.get("username"),
        'email': session.get("email"),
        'first_name': session.get("first_name"),
        'last_name': session.get("last_name"),
        'profile_image': session.get("profile_image"),
        'role': session.get("role"),
        'can_share': session.get("can_share"),
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
    session.modified = True  # Ensure the session is marked as modified.

def update_user_role(user_id):
    user = repository.get_user_by_id(user_id)
    if user['role'] == "traveller":
        repository.update_user_role(user_id, "member")

@app.route('/subscription/list', methods=['GET','POST'])
@login_required
def get_subscriptions():
    """
    Get all subscription by user_id
    """
    if request.method == 'POST':
        user_id = request.form.get("user_id")
    else:
        user_id = session.get("user_id")
    
    subscriptions = repository.get_subscriptions_by_user_id(user_id)
    return {'success': True, "subscriptions": subscriptions}

@app.route('/subscription/detail', methods=['GET'])
@login_required
def get_subscription():
    """Get subscription details"""
    subscription_id = request.args.get('subscription_id')
    if not subscription_id:
        return jsonify({"success": False, "error": "Missing subscription_id parameter"})
    
    subscription = repository.get_subscription_by_id(subscription_id)
    if not subscription:
        return jsonify({"success": False, "error": "Subscription not found"})
    
    # get plan detail
    plan = repository.get_plan_by_id(subscription['plan_id'])
    if plan:
        subscription['plan_name'] = plan['name']
    
    return jsonify({
        "success": True,
        "subscription": subscription
    })

@app.route('/plans', methods=['GET'])
@login_required
def plans():
    """
    Get all plans
    """
    plans = repository.get_plans()
    return {'success': True, "plans": plans}

@app.route('/plan', methods=['POST'])
@login_required
def plan():
    """
    Get plan details by id
    """
    plan_id = request.form.get("plan_id")
    plan = repository.get_plan_by_id(plan_id)
    return {'success': True, "plan": plan}

@app.route('/admin/grant-subscription', methods=['POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def grant_subscription():
    """Administrator grants free subscription"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid request data'})
            
        user_id = data.get('user_id')
        months = data.get('months', 1)
        
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id parameter'})
        
        # get user detail
        user = repository.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'})
        
        #（plan_id = 2，One Month plan）
        plan = repository.get_subscription_plan(2)  # One Month plan
        if not plan:
            return jsonify({'success': False, 'error': 'Subscription plan not found'})
        
        # Set subscription time
        start_date = datetime.now()
        end_date = start_date + timedelta(days=30 * months) 
        
        # craete subscription record
        subscription_id = repository.create_subscription(
            user_id=user_id,
            plan_id=plan['id'],
            start_date=start_date,
            end_date=end_date,
            payment_amount=0.00,
            gst_amount=0.00,
            billing_country='NZ',
            is_free_trial=False,
            granted_by_admin=True
        )
        
        if not subscription_id:
            return jsonify({'success': False, 'error': 'Failed to create subscription record'})
        
        # update user role
        if user['role'] == 'traveller':
            repository.update_user_role(user_id, 'member')
        
        return jsonify({'success': True, 'subscription_id': subscription_id})
        
    except Exception as e:
        current_app.logger.error(f"Error in grant_subscription: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/user-subscription-history', methods=['POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def get_user_subscription_history():
    """Get all subscription history for a user (admin only)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'Missing user_id parameter'})
        subscriptions = repository.get_subscriptions_by_user_id(user_id)
        return jsonify({
            'success': True,
            'subscriptions': subscriptions
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_user_subscription_history: {str(e)}")
        return jsonify({'success': False, 'error': 'An unexpected error occurred while loading subscription history.'})

@app.route('/subscription/history', methods=['GET'])
@login_required
def get_subscription_history():
    """get subscription history"""
    try:
        user_id = session.get('user_id')
        subscriptions = repository.get_subscriptions_by_user_id(user_id)
        return jsonify({
            'success': True,
            'subscriptions': subscriptions
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_subscription_history: {str(e)}")
        return jsonify({'success': False, 'error': 'failed to get subscription history'})

@app.route('/subscription/detail', methods=['POST'])
@login_required
def get_subscription_detail():
    """Get subscription details and payment history"""
    try:
        data = request.get_json()
        subscription_id = data.get('subscription_id')
        user_id = session.get('user_id')
        
        if not subscription_id:
            return jsonify({'success': False, 'error': 'Missing subscription ID parameter'})
            
        # Get subscription information.
        subscription = repository.get_subscription_by_id(subscription_id)
        if not subscription:
            return jsonify({'success': False, 'error': 'No subscription record found'})
            
        # Verify permissions (only view own subscriptions or admin can view all)
        if subscription['user_id'] != user_id and session.get('role') not in ['admin', 'editor']:
            return jsonify({'success': False, 'error': 'No permission to view this subscription record'})
            
        # get payment history
        payment_history = repository.get_payment_history_by_subscription_id(subscription_id)
        
        return jsonify({
            'success': True,
            'subscription': subscription,
            'payment_history': payment_history
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_subscription_detail: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to get subscription details'})

@app.route('/subscription-history')
@login_required
def subscription_history():
    """Subscription history page"""
    return render_template('subscription_history.html')

@app.route('/admin/subscription-detail', methods=['POST'])
@login_required
@role_required(Role.ADMIN.value, Role.SUPPORT_TECHS.value)
def get_admin_subscription_detail():
    """Administrator gets subscription details and payment history"""
    try:
        data = request.get_json()
        subscription_id = data.get('subscription_id')
        
        current_app.logger.info(f"Admin requesting subscription detail for ID: {subscription_id}")
        
        if not subscription_id:
            current_app.logger.error("Missing subscription_id parameter")
            return jsonify({'success': False, 'error': 'Missing subscription ID parameter'})
            
        # get subscription detail
        subscription = repository.get_subscription_by_id(subscription_id)
        if not subscription:
            current_app.logger.error(f"Subscription not found for ID: {subscription_id}")
            return jsonify({'success': False, 'error': 'system error'})
            
        # get payment history
        payment_history = repository.get_payment_history_by_subscription_id(subscription_id)
        
        current_app.logger.info(f"Successfully retrieved subscription detail for ID: {subscription_id}")
        
        return jsonify({
            'success': True,
            'subscription': subscription,
            'payment_history': payment_history
        })
    except Exception as e:
        current_app.logger.error(f"Error in get_admin_subscription_detail: {str(e)}")
        return jsonify({'success': False, 'error': 'failed to get subscription history'})


@app.route('/subscription/export-pdf', methods=['GET'])
@login_required
def export_subscription_pdf():
    subscription_id = request.args.get('subscription_id')
    if not subscription_id:
        return jsonify({'success': False, 'error': 'Subscription ID is required'}), 400

    subscription = repository.get_subscription_by_id(subscription_id)
    if not subscription:
        return jsonify({'success': False, 'error': 'Subscription not found'}), 404

    # Generate PDF
    pdf_buffer = generate_subscription_pdf(subscription)

    # Create a BytesIO object from the PDF buffer
    pdf_io = io.BytesIO(pdf_buffer)
    pdf_io.seek(0)

    # Send the PDF file
    return send_file(
        pdf_io,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'subscription-detail-{subscription["id"]}.pdf'
    )
