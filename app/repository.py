from app import db
import json
from datetime import datetime, date

"""
all the functions below are used to interact with the database
"""

def _json_serial(obj):
    """
    JSON
    """
    if isinstance(obj, (datetime, date)):
        return obj.strftime('%Y-%m-%d')
    raise TypeError(f"Type {type(obj)} not serializable")

def create_user(username, password_hash, email, first_name, last_name, location_id, role="traveller"):
    """create a new user"""
    query = """
    INSERT INTO users (username, password_hash, email, first_name, last_name, location_id, role, can_share, can_publish)
    VALUES (%s, %s, %s, %s, %s, %s, %s, true, false)
    """
    return db.execute_db(query, (username, password_hash, email, first_name, last_name, location_id, role))


def get_user_by_username(username):
    """get user by username"""
    query = "SELECT * FROM users WHERE username = %s LIMIT 1"
    return db.query_db(query, (username,), fetch_one=True)


def get_user_by_id(user_id):
    """get user by user_id"""
    query = "SELECT * FROM users WHERE id = %s LIMIT 1"
    return db.query_db(query, (user_id,), fetch_one=True)


def update_user_status(user_id, status):
    """update user status"""
    query = "UPDATE users SET status = %s WHERE id = %s"
    return db.execute_db(query, (status, user_id))


def update_user_role(user_id, role):
    """update user role"""
    query = "UPDATE users SET role = %s WHERE id = %s"
    return db.execute_db(query, (role, user_id))


def update_user_can_share(user_id, can_share):
    """update user can_share status"""
    query = "UPDATE users SET can_share = %s WHERE id = %s"
    return db.execute_db(query, (can_share, user_id))

def update_user_can_publish(user_id, can_publish):
    """update user can_publish status"""
    query = "UPDATE users SET can_publish = %s WHERE id = %s"
    return db.execute_db(query, (can_publish, user_id))

def update_user_password(user_id, new_password_hash):
    """update user password"""
    query = "UPDATE users SET password_hash = %s WHERE id = %s"
    return db.execute_db(query, (new_password_hash, user_id))


def update_user_profile_image(user_id, profile_image):
    """update user profile images"""
    query = "UPDATE users SET profile_image = %s WHERE id = %s"
    return db.execute_db(query, (profile_image, user_id))


def update_user_profile(user_id, email, first_name, last_name, location_id, description):
    """update user profile"""
    query = "UPDATE users SET email = %s, first_name = %s, last_name = %s, location_id = %s, description = %s WHERE id = %s"
    return db.execute_db(query, (email, first_name, last_name, location_id, description, user_id))


def get_user_page(status=None, role=None, keyword=None, page=1, per_page=2, search_type=None, can_share=None):
    """Filter users by status and search with pagination using SQL"""
    query = """
        SELECT SQL_CALC_FOUND_ROWS * FROM users
        WHERE 1=1
    """
    params = []

    if status:
        query += " AND status = %s"
        params.append(status)

    if role:
        query += " AND role = %s"
        params.append(role)

    if can_share:
        query += " AND can_share = %s"
        params.append(bool(int(can_share)))

    if keyword:
        if search_type == 'first_name':
            query += " AND LOWER(first_name) LIKE %s"
            search_term = f"%{keyword.lower()}%"
            params.append(search_term)
        elif search_type == 'last_name':
            query += " AND LOWER(last_name) LIKE %s"
            search_term = f"%{keyword.lower()}%"
            params.append(search_term)
        elif search_type == 'username':
            query += " AND LOWER(username) LIKE %s"
            search_term = f"%{keyword.lower()}%"
            params.append(search_term)
        elif search_type == 'email':
            query += " AND LOWER(email) LIKE %s"
            search_term = f"%{keyword.lower()}%"
            params.append(search_term)

    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    # get users
    users = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return users, total, total_pages


def get_journeys_page(user_id, current_page, per_page, is_public=None, is_hidden=None, keyword=None, location_ids=None, tab=None):
    """get journeys page"""
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        j.*,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        CASE 
            WHEN u.role IN ('admin', 'editor') THEN TRUE
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = j.user_id 
                AND us.end_date > NOW()
            ) THEN TRUE
            ELSE FALSE
        END as has_active_subscription,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo,
        CASE 
            WHEN %s IS NULL THEN FALSE
            ELSE EXISTS (
                SELECT 1 FROM follows f 
                WHERE f.follower_id = %s 
                AND f.followed_type = 'journey' 
                AND f.followed_id = j.id
            )
        END as is_following
    FROM journeys j
    LEFT JOIN users u ON j.user_id = u.id
    WHERE 1=1
    """
    params = [user_id, user_id]

    if user_id and tab == 'my':
        query += " AND j.user_id = %s"
        params.append(user_id)
    elif tab == 'following' and user_id:
        query += """ AND EXISTS (
            SELECT 1 FROM follows f 
            WHERE f.follower_id = %s 
            AND f.followed_type = 'journey' 
            AND f.followed_id = j.id
        )"""
        params.append(user_id)

    if is_public is not None:
        if is_public is True:
            query += """ AND (
                j.is_published = TRUE 
                OR (j.is_public = TRUE AND u.role IN ('admin', 'editor'))
                OR (j.is_public = TRUE AND EXISTS (
                    SELECT 1 FROM user_subscriptions us 
                    WHERE us.user_id = j.user_id 
                    AND us.end_date > NOW()
                ))
            )"""
        else:
            query += " AND j.is_public = %s"
            params.append(is_public)

    if is_hidden is not None:
        query += " AND j.is_hidden = %s"
        params.append(is_hidden)

    if keyword:
        query += " AND (LOWER(j.title) LIKE %s OR LOWER(j.description) LIKE %s)"
        search_term = f"%{keyword.lower()}%"
        params.extend([search_term, search_term])

    if location_ids:
        placeholders = ','.join(['%s'] * len(location_ids))
        query += f" AND j.id IN (SELECT e.journey_id FROM events e WHERE e.location_id IN ({placeholders}))"
        params.extend(location_ids)

    query += " ORDER BY j.start_date DESC, j.created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (current_page - 1) * per_page])

    # get journeys
    journeys = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return journeys, total, total_pages


def create_journey(user_id, title, description, is_public, is_published, start_date):
    """create a new journey"""
    query = """
    INSERT INTO journeys (user_id, title, description, is_public, is_published, start_date)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    return db.execute_db(query, (user_id, title, description, is_public, is_published, start_date))


def get_journey_by_id(journey_id):
    """get journey by journey_id"""
    query = """
    SELECT j.*, 
           (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo
    FROM journeys j 
    WHERE j.id = %s 
    LIMIT 1
    """
    return db.query_db(query, (journey_id,), fetch_one=True)


def get_events_by_journey_id(journey_id):
    """get events by journey_id"""
    query = """
    SELECT e.*, GROUP_CONCAT(p.photo_url) AS photo_urls, l.name AS location_name
    FROM events e
    LEFT JOIN photos p ON e.id = p.event_id
    LEFT JOIN locations l ON e.location_id = l.id
    WHERE e.journey_id = %s
    GROUP BY e.id, l.name
    ORDER BY e.start_datetime
    """
    return db.query_db(query, (journey_id,), fetch_all=True)


def update_journey_public(journey_id, is_public):
    """update journey public status"""
    query = "UPDATE journeys SET is_public = %s WHERE id = %s"
    return db.execute_db(query, (is_public, journey_id))


def update_journey_hidden(journey_id, is_hidden):
    """update journey hidden"""
    query = "UPDATE journeys SET is_hidden = %s WHERE id = %s"
    return db.execute_db(query, (is_hidden, journey_id))

def update_journey_published(journey_id, is_published):
    """update journey published status"""
    query = "UPDATE journeys SET is_published = %s WHERE id = %s"
    return db.execute_db(query, (is_published, journey_id))

def update_journey_no_edit(journey_id, no_edit):
    query = "UPDATE journeys SET no_edit = %s WHERE id = %s"
    return db.execute_db(query, (no_edit, journey_id))


def get_or_create_location_id(location_name):
    """get or create location_id"""
    location = get_location_by_name(location_name)
    if location:
        location_id = location['id']
    else:
        query = "INSERT INTO locations (name) VALUES (%s)"
        location_id = db.execute_db(query, (location_name,))
    return location_id

def get_location_by_name(location_name):
    """get location by location_name"""
    query = "SELECT * FROM locations WHERE name = %s LIMIT 1"
    return db.query_db(query, (location_name,), fetch_one=True)

def get_locations_like_name(location_name):
        """get location ids by location_name"""
        query = "SELECT * FROM locations WHERE name LIKE %s"
        return db.query_db(query, (f"%{location_name}%",), fetch_all=True)


def get_location_by_id(location_id):
    """get location by location_id"""
    query = "SELECT * FROM locations WHERE id = %s LIMIT 1"
    return db.query_db(query, (location_id,), fetch_one=True)


def get_newest_journeys_by_user_id(user_id, limit=5):
    """get latest journeys for a user"""
    query = """
    SELECT 
        j.*,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo
    FROM journeys j
    LEFT JOIN users u ON j.user_id = u.id
    WHERE j.user_id = %s AND j.is_hidden = FALSE
    ORDER BY j.start_date DESC
    LIMIT %s
    """
    return db.query_db(query, (user_id, limit), fetch_all=True)


def get_locations():
    """get all locations"""
    query = "SELECT * FROM locations"
    return db.query_db(query, fetch_all=True)


def create_event(journey_id, title, description, start_datetime, end_datetime, location_id):
    """create a new event"""
    query = """
    INSERT INTO events (journey_id, title, description, start_datetime, end_datetime, location_id)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    return db.execute_db(query, (journey_id, title, description, start_datetime, end_datetime, location_id))


def create_event_photo(event_id, photo_url, display_order):
    """create event photo"""
    query = "INSERT INTO photos (event_id, photo_url, display_order) VALUES (%s, %s, %s)"
    return db.execute_db(query, (event_id, photo_url, display_order))


def update_event_photo(photo_id, photo_url):
    """update event photo"""
    query = "UPDATE photos SET photo_url = %s WHERE id = %s"
    return db.execute_db(query, (photo_url, photo_id))


def update_event_photo_order(event_id, photo_url, display_order):
    query = "UPDATE photos SET display_order = %s WHERE event_id = %s AND photo_url = %s"
    return db.execute_db(query, (display_order, event_id, photo_url))


def update_journey(journey_id, title, description, start_date):
    """update journey"""
    query = "UPDATE journeys SET title = %s, description = %s, start_date = %s WHERE id = %s"
    return db.execute_db(query, (title, description, start_date, journey_id))


def delete_journey(journey_id):
    """delete journey"""
    query = "DELETE FROM journeys WHERE id = %s"
    return db.execute_db(query, (journey_id,))


def update_event(event_id, title, description, start_date, end_date, location_id):
    """update journey"""
    query = "UPDATE events SET title = %s, description = %s, start_datetime = %s, end_datetime = %s, location_id = %s WHERE id = %s"
    return db.execute_db(query, (title, description, start_date, end_date, location_id, event_id))


def get_photos_by_event_id(event_id):
    """get photos by event_id"""
    query = "SELECT * FROM photos WHERE event_id = %s ORDER BY display_order ASC, id ASC"
    return db.query_db(query, (event_id,), fetch_all=True)


def get_user_by_email(email):
    """get user by email"""
    query = "SELECT * FROM users WHERE email = %s LIMIT 1"
    return db.query_db(query, (email,), fetch_one=True)


def delete_event_photo(event_id):
    """delete event photo"""
    query = "DELETE FROM photos WHERE event_id = %s"
    return db.execute_db(query, (event_id,))


def delete_event_photo_by_id(photo_id):
    """delete event photo by photo id"""
    query = "DELETE FROM photos WHERE id = %s"
    return db.execute_db(query, (photo_id,))


def delete_event(event_id):
    """delete event"""
    query = "DELETE FROM events WHERE id = %s"
    return db.execute_db(query, (event_id,))


def get_location_page(keyword, current_page, per_page):
    """get location page"""
    query = """
    SELECT SQL_CALC_FOUND_ROWS * FROM locations
    WHERE 1=1
    """
    params = []

    if keyword:
        query += " AND LOWER(name) LIKE %s"
        search_term = f"%{keyword.lower()}%"
        params.append(search_term)

    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (current_page - 1) * per_page])

    # get locations
    locations = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return locations, total, total_pages


def get_announcements(limit=5):
    """get latest announcements"""
    query = """
    SELECT a.*, u.first_name, u.last_name, u.profile_image
    FROM announcements a
    LEFT JOIN users u ON a.user_id = u.id
    ORDER BY a.created_at DESC
    LIMIT %s
    """
    return db.query_db(query, (limit,), fetch_all=True)


def create_announcement(user_id, title, content):
    """create a new announcement"""
    query = """
    INSERT INTO announcements (user_id, title, content)
    VALUES (%s, %s, %s)
    """
    return db.execute_db(query, (user_id, title, content))


def get_journeys(user_id):
    """get all journeys for a user"""
    query = """
    SELECT 
        j.*,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo
    FROM journeys j
    LEFT JOIN users u ON j.user_id = u.id
    WHERE j.user_id = %s
    ORDER BY j.start_date DESC, j.created_at DESC
    """
    return db.query_db(query, (user_id,), fetch_all=True)


def get_event_by_id(event_id):
    """get event by event_id"""
    query = "SELECT * FROM events WHERE id = %s LIMIT 1"
    return db.query_db(query, (event_id,), fetch_one=True)


def get_user_journeys_count(user_id):
    """get total number of journeys for a user"""
    query = "SELECT COUNT(*) AS count FROM journeys WHERE user_id = %s"
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0


def get_user_events_count(user_id):
    """get total number of events for a user"""
    query = """
    SELECT COUNT(*) AS count 
    FROM events e 
    JOIN journeys j ON e.journey_id = j.id 
    WHERE j.user_id = %s
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0


def get_all_users_count():
    """get total number of users in the system"""
    query = "SELECT COUNT(*) AS count FROM users"
    result = db.query_db(query, fetch_one=True)
    return result['count'] if result else 0


def get_public_journeys_count():
    """get total number of public journeys in the system"""
    query = "SELECT COUNT(*) AS count FROM journeys WHERE is_public = TRUE AND is_hidden = FALSE"
    result = db.query_db(query, fetch_one=True)
    return result['count'] if result else 0


def get_subscription_plans():
    """Get all available subscription plans"""
    query = "SELECT * FROM subscription_plans ORDER BY price_nz"
    return db.query_db(query, fetch_all=True)


def get_current_subscription(user_id):
    """Get the user's current subscription information"""
    query = """
        SELECT us.*, sp.name as plan_name 
        FROM user_subscriptions us
        JOIN subscription_plans sp ON us.plan_id = sp.id
        WHERE us.user_id = %s AND us.end_date > NOW()
        ORDER BY us.end_date DESC 
        LIMIT 1
    """
    return db.query_db(query, (user_id,), fetch_one=True)


def can_start_free_trial(user_id):
    """Check if the user can start a free trial"""
    query = """
        SELECT COUNT(*) as count 
        FROM user_subscriptions 
        WHERE user_id = %s AND is_free_trial = TRUE
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] == 0


def get_free_trial_plan():
    """Get the free trial plan"""
    query = "SELECT * FROM subscription_plans WHERE months = 0 LIMIT 1"
    return db.query_db(query, fetch_one=True)


def create_subscription(user_id, plan_id, start_date, end_date, payment_amount, gst_amount, billing_country, is_free_trial=False, granted_by_admin=False):
    """Create subscription record"""
    query = """
    INSERT INTO user_subscriptions 
    (user_id, plan_id, start_date, end_date, payment_amount, gst_amount, 
     billing_country, is_free_trial, granted_by_admin)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    return db.execute_db(query, (
        user_id, plan_id, start_date, end_date, 
        payment_amount, gst_amount, billing_country,
        is_free_trial, granted_by_admin
    ))


def get_subscription_plan(plan_id):
    """Get subscription plan information"""
    query = "SELECT * FROM subscription_plans WHERE id = %s"
    return db.query_db(query, (plan_id,), fetch_one=True)

def get_latest_subscription_by_id(user_id):
    """get latest subscription details for a user"""
    query = """
    SELECT us.*, sp.name as plan_name, sp.price_nz, sp.price_other, sp.months, sp.discount
    FROM user_subscriptions us LEFT JOIN subscription_plans sp
    ON us.plan_id = sp.id 
    WHERE us.user_id = %s 
    ORDER BY us.created_at DESC 
    LIMIT 1;
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result

def get_subscriptions_by_user_id(user_id):
    """get subscription list by user id"""
    query = """
    SELECT us.*, sp.name as plan_name, sp.price_nz, sp.price_other, sp.months, sp.discount
    FROM user_subscriptions us LEFT JOIN subscription_plans sp
    ON us.plan_id = sp.id 
    WHERE us.user_id = %s 
    ORDER BY us.created_at;
    """
    result = db.query_db(query, (user_id,), fetch_all=True)
    return result

def get_subscription_by_id(subscription_id):
    """get subscription by subscription id"""
    query = """
    SELECT 
        us.*,
        sp.name as plan_name,
        sp.price_nz,
        sp.price_other,
        sp.months,
        sp.discount
    FROM user_subscriptions us 
    LEFT JOIN subscription_plans sp ON us.plan_id = sp.id 
    WHERE us.id = %s;
    """
    result = db.query_db(query, (subscription_id,), fetch_one=True)
    return result

def get_plan_by_id(plan_id):
    """get plan"""
    query = """
    SELECT * 
    FROM subscription_plans 
    WHERE id = %s;
    """
    return db.query_db(query, (plan_id,), fetch_one=True)

def get_plans():
    """get all plans"""
    query = """
    SELECT * 
    FROM subscription_plans 
    WHERE price_nz > 0 OR price_other > 0;
    """
    return db.query_db(query,(), fetch_all=True)

def get_published_journeys_page(current_page, per_page, is_hidden=False):
    """get published journeys page"""
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        j.*,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        CASE 
            WHEN u.role IN ('admin', 'editor') THEN TRUE
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = j.user_id 
                AND us.end_date > NOW()
            ) THEN TRUE
            ELSE FALSE
        END as has_active_subscription,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo
    FROM journeys j
    LEFT JOIN users u ON j.user_id = u.id
    WHERE j.is_hidden = %s
    AND j.is_published = TRUE
    AND (
        u.role IN ('admin', 'editor')
        OR EXISTS (
            SELECT 1 FROM user_subscriptions us 
            WHERE us.user_id = j.user_id 
            AND us.end_date > NOW()
        )
    )
    """
    params = [is_hidden]

    query += " ORDER BY j.start_date DESC, j.created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (current_page - 1) * per_page])

    # get journeys
    journeys = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return journeys, total, total_pages

def get_payment_history_by_subscription_id(subscription_id):
    """Get the payment history for the subscription"""
    query = """
    SELECT * 
    FROM payment_history 
    WHERE subscription_id = %s 
    ORDER BY payment_date DESC;
    """
    return db.query_db(query, (subscription_id,), fetch_all=True)

def get_covers_by_journey_id(journey_id):
    """
    Get all covers for a journey
    """
    query = "SELECT * FROM covers WHERE journey_id = %s"
    return db.query_db(query, (journey_id,), fetch_all=True)

def create_journey_cover(journey_id, photo_url):
    """
    Create a new journey cover
    """
    query = "INSERT INTO covers (journey_id, photo_url) VALUES (%s, %s)"
    return db.execute_db(query, (journey_id, photo_url))

def update_journey_cover(cover_id, photo_url):
    """
    Update a journey cover
    """
    query = "UPDATE covers SET photo_url = %s WHERE id = %s"
    return db.execute_db(query, (photo_url, cover_id))

def delete_journey_cover(journey_id):
    """
    Delete a journey cover
    """
    query = "DELETE FROM covers WHERE journey_id = %s"
    return db.execute_db(query, (journey_id,))

def create_comment(event_id, user_id, content):
    """
    Create a new comment
    """
    query = """
    INSERT INTO comments (event_id, user_id, content) 
    VALUES (%s, %s, %s)
    """
    return db.execute_db(query, (event_id, user_id, content))

def get_comments_by_event_id(event_id, user_id, sort_by='newest'):
    """
    Get comments for an event with sorting options
    """
    # Base query
    query = """
        SELECT 
            c.*,
            u.username,
            u.profile_image,
            (SELECT COUNT(*) FROM comment_reactions WHERE comment_id = c.id AND reaction_type = 'like') as like_count,
            (SELECT COUNT(*) FROM comment_reactions WHERE comment_id = c.id AND reaction_type = 'dislike') as dislike_count,
            (SELECT reaction_type FROM comment_reactions WHERE comment_id = c.id AND user_id = %s) as user_reaction
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.event_id = %s
        AND c.is_hidden = FALSE
    """
    
    # Add sorting
    if sort_by == 'newest':
        query += ' ORDER BY c.created_at DESC'
    elif sort_by == 'oldest':
        query += ' ORDER BY c.created_at ASC'
    elif sort_by == 'most_liked':
        query += ' ORDER BY like_count DESC, c.created_at DESC'
    
    return db.query_db(query, (user_id, event_id), fetch_all=True)

def get_comment_by_id(comment_id):
    """
    Get a comment by its ID
    """
    query = "SELECT * FROM comments WHERE id = %s"
    return db.query_db(query, (comment_id,), fetch_one=True)

def delete_comment(comment_id):
    """
    Delete a comment
    """
    query = "DELETE FROM comments WHERE id = %s"
    return db.execute_db(query, (comment_id,))

def create_event_reaction(event_id, user_id):
    """
    Create a new event reaction (like)
    """
    query = """
    INSERT INTO event_reactions (event_id, user_id, reaction_type) 
    VALUES (%s, %s, %s)
    """
    return db.execute_db(query, (event_id, user_id, 'like'))

def get_event_reaction(event_id, user_id):
    """
    Get a user's reaction to an event
    """
    query = """
    SELECT * FROM event_reactions 
    WHERE event_id = %s AND user_id = %s
    """
    return db.query_db(query, (event_id, user_id), fetch_one=True)

def delete_event_reaction(reaction_id):
    """
    Delete an event reaction
    """
    query = "DELETE FROM event_reactions WHERE id = %s"
    return db.execute_db(query, (reaction_id,))

def get_event_like_count(event_id):
    """
    Get the number of likes for an event
    """
    query = """
    SELECT COUNT(*) as count 
    FROM event_reactions 
    WHERE event_id = %s
    """
    result = db.query_db(query, (event_id,), fetch_one=True)
    return result['count'] if result else 0

def get_conversations(user_id):
    """
    Get all conversations for a user
    """
    try:
        # Get system user information
        system_user = get_system_user()
        
        # Get all conversations
        query = """
            SELECT DISTINCT 
                CASE 
                    WHEN pm.sender_id = %s THEN pm.receiver_id
                    ELSE pm.sender_id
                END as other_user_id,
                u.first_name,
                u.last_name,
                u.profile_image,
                (
                    SELECT content 
                    FROM private_messages
                    WHERE (sender_id = %s AND receiver_id = other_user_id)
                       OR (sender_id = other_user_id AND receiver_id = %s)
                    ORDER BY created_at DESC 
                    LIMIT 1
                ) as last_message,
                (
                    SELECT created_at 
                    FROM private_messages
                    WHERE (sender_id = %s AND receiver_id = other_user_id)
                       OR (sender_id = other_user_id AND receiver_id = %s)
                    ORDER BY created_at DESC 
                    LIMIT 1
                ) as last_message_time,
                (
                    SELECT COUNT(*) 
                    FROM private_messages 
                    WHERE sender_id = other_user_id 
                    AND receiver_id = %s 
                    AND is_read = 0
                ) as unread_count
            FROM private_messages pm
            LEFT JOIN users u ON (
                CASE 
                    WHEN pm.sender_id = %s THEN pm.receiver_id
                    ELSE pm.sender_id
                END = u.id
            )
            WHERE pm.sender_id = %s OR pm.receiver_id = %s
            ORDER BY last_message_time DESC
        """
        conversations = db.query_db(query, (
            user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id, user_id
        ), fetch_all=True)
        
        # deal with message
        for conv in conversations:
            if conv['other_user_id'] == 0:
                conv['first_name'] = system_user['first_name']
                conv['last_name'] = system_user['last_name']
                conv['profile_image'] = system_user['profile_image']
        
        return conversations
    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
        return []

def get_messages_by_conversation(conversation_id, user_id):
    """
    Get messages by conversation id
    """
    try:
        # get user detail
        system_user = get_system_user()
        
        # get message
        query = """
            SELECT pm.*, 
                   u.username, u.first_name, u.last_name, u.profile_image
            FROM private_messages pm
            LEFT JOIN users u ON pm.sender_id = u.id
            WHERE (pm.sender_id = %s AND pm.receiver_id = %s)
               OR (pm.sender_id = %s AND pm.receiver_id = %s)
            ORDER BY pm.created_at ASC
        """
        messages = db.query_db(query, (user_id, conversation_id, conversation_id, user_id), fetch_all=True)
        
        # deal with system message
        for message in messages:
            if message['sender_id'] == 0:
                message['username'] = system_user['username']
                message['first_name'] = system_user['first_name']
                message['last_name'] = system_user['last_name']
                message['profile_image'] = system_user['profile_image']
        
        return messages
    except Exception as e:
        print(f"Error getting messages: {str(e)}")
        return []

def create_message(sender_id, receiver_id, content):
    """crate new message"""
    query = """
    INSERT INTO private_messages (sender_id, receiver_id, content)
    VALUES (%s, %s, %s)
    """
    return db.execute_db(query, (sender_id, receiver_id, content))

def mark_message_read(message_id, user_id):
    """mark message as read"""
    query = """
    UPDATE private_messages 
    SET is_read = TRUE 
    WHERE id = %s AND receiver_id = %s
    """
    return db.execute_db(query, (message_id, user_id))

def can_send_message(user):
    """Check if the user has permission to send messages"""
    if user['role'] in ['admin', 'editor']:
        return True
        
    # Check if there is a valid subscription
    query = """
    SELECT 1 FROM user_subscriptions 
    WHERE user_id = %s AND end_date > NOW()
    LIMIT 1
    """
    result = db.query_db(query, (user['id'],), fetch_one=True)
    return bool(result)


def get_unread_messages_count(user_id):
    """Get the user's unread message count"""
    query = """
    SELECT COUNT(*) as count 
    FROM private_messages 
    WHERE receiver_id = %s AND is_read = FALSE
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0

def toggle_comment_reaction(comment_id, user_id, reaction_type):
    """
    Toggle a reaction (like/dislike) on a comment
    Returns: 'added' if reaction was added, 'removed' if reaction was removed
    """
    try:
        # Check if user already has a reaction
        query = """
            SELECT reaction_type 
            FROM comment_reactions 
            WHERE comment_id = %s AND user_id = %s
        """
        existing_reaction = db.query_db(query, (comment_id, user_id), fetch_one=True)
        
        if existing_reaction:
            if existing_reaction['reaction_type'] == reaction_type:
                # Remove reaction if clicking the same type
                query = """
                    DELETE FROM comment_reactions 
                    WHERE comment_id = %s AND user_id = %s
                """
                db.execute_db(query, (comment_id, user_id))
                return 'removed'
            else:
                # Change reaction type
                query = """
                    UPDATE comment_reactions 
                    SET reaction_type = %s 
                    WHERE comment_id = %s AND user_id = %s
                """
                db.execute_db(query, (reaction_type, comment_id, user_id))
                return 'added'
        else:
            # Add new reaction
            query = """
                INSERT INTO comment_reactions (comment_id, user_id, reaction_type)
                VALUES (%s, %s, %s)
            """
            db.execute_db(query, (comment_id, user_id, reaction_type))
            return 'added'
            
    except Exception as e:
        print(f"Error in toggle_comment_reaction: {str(e)}")
        return None

def get_comment_reactions(comment_id):
    """
    Get reaction counts for a comment
    """
    try:
        query = """
            SELECT 
                SUM(CASE WHEN reaction_type = 'like' THEN 1 ELSE 0 END) as like_count,
                SUM(CASE WHEN reaction_type = 'dislike' THEN 1 ELSE 0 END) as dislike_count
            FROM comment_reactions 
            WHERE comment_id = %s
        """
        result = db.query_db(query, (comment_id,), fetch_one=True)
        return result or {'like_count': 0, 'dislike_count': 0}
    except Exception as e:
        print(f"Error in get_comment_reactions: {str(e)}")
        return {'like_count': 0, 'dislike_count': 0}

def create_comment_report(comment_id, reporter_id, report_type, content):
    """
    Create a new comment report
    """
    query = """
    INSERT INTO comment_reports (comment_id, reporter_id, report_type, content) 
    VALUES (%s, %s, %s, %s)
    """
    return db.execute_db(query, (comment_id, reporter_id, report_type, content))

def hide_comment(comment_id):
    """
    Hide a comment
    """
    query = "UPDATE comments SET is_hidden = TRUE WHERE id = %s"
    return db.execute_db(query, (comment_id,))

def get_comment_reports(page=1, per_page=10):
    """
    Get reported comments with pagination
    """
    # Get total count
    count_query = "SELECT COUNT(*) as total FROM comment_reports WHERE status = 'pending'"
    total = db.query_db(count_query, fetch_one=True)['total']
    
    # Get reports with comment and user information
    query = """
        SELECT 
            r.id as report_id,
            r.comment_id,
            r.report_type,
            r.content as report_content,
            r.created_at as report_date,
            c.content as comment_content,
            c.is_hidden,
            u.username as comment_author,
            u.role as comment_author_role,
            r2.username as reporter_name
        FROM comment_reports r
        JOIN comments c ON r.comment_id = c.id
        JOIN users u ON c.user_id = u.id
        JOIN users r2 ON r.reporter_id = r2.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at DESC
        LIMIT %s OFFSET %s
    """
    reports = db.query_db(query, (per_page, (page - 1) * per_page), fetch_all=True)
    
    return {
        'reports': reports,
        'total': total,
        'page': page,
        'per_page': per_page,
        'total_pages': (total + per_page - 1) // per_page
    }

def resolve_comment_report(report_id, action):
    """
    Resolve a comment report
    """
    if action == 'hide':
        # Get comment_id from report
        query = "SELECT comment_id FROM comment_reports WHERE id = %s"
        result = db.query_db(query, (report_id,), fetch_one=True)
        if result:
            comment_id = result['comment_id']
            # Hide the comment
            hide_query = "UPDATE comments SET is_hidden = TRUE WHERE id = %s"
            db.execute_db(hide_query, (comment_id,))
    
    # Update report status
    query = "UPDATE comment_reports SET status = 'resolved' WHERE id = %s"
    return db.execute_db(query, (report_id,))

def escalate_comment_report(report_id, reason):
    """
    Escalate a comment report to admin team
    """
    query = """
    UPDATE comment_reports 
    SET status = 'escalated', 
        content = CONCAT(content, '\n\nEscalation reason: ', %s) 
    WHERE id = %s
    """
    return db.execute_db(query, (reason, report_id))

def update_user_profile_visibility(user_id, is_public):
    """Update user visibility settings in the public directory"""
    query = "UPDATE users SET is_public_profile = %s WHERE id = %s"
    return db.execute_db(query, (is_public, user_id))

def get_public_users_page(keyword=None, page=1, per_page=10):
    """Get a list of public users, supporting search by first name and last name"""
    query = """
        SELECT SQL_CALC_FOUND_ROWS 
            u.*,
            l.name as location_name,
            (SELECT COUNT(*) FROM journeys j 
             WHERE j.user_id = u.id 
             AND j.is_public = TRUE 
             AND j.is_hidden = FALSE) as public_journeys_count
        FROM users u
        LEFT JOIN locations l ON u.location_id = l.id
        WHERE u.status = 'active'
        AND u.is_public_profile = TRUE
    """
    params = []

    if keyword:
        query += """ AND (
            LOWER(u.first_name) LIKE %s 
            OR LOWER(u.last_name) LIKE %s
            OR LOWER(CONCAT(u.first_name, ' ', u.last_name)) LIKE %s
        )"""
        search_term = f"%{keyword.lower()}%"
        params.extend([search_term, search_term, search_term])

    query += " ORDER BY u.first_name ASC, u.last_name ASC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    # get user list
    users = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return users, total, total_pages

def get_user_events(user_id, page=1, per_page=10, only_public=True):
    """Get user event feed (based on event table)"""
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        e.id as event_id,
        e.title as event_title,
        e.start_datetime as event_time,
        e.description as event_description,
        j.id as journey_id,
        j.title as journey_title,
        l.name as location_name,
        (SELECT COUNT(*) FROM event_reactions WHERE event_id = e.id) as like_count,
        (SELECT COUNT(*) FROM comments WHERE event_id = e.id) as comment_count,
        (SELECT COUNT(*) FROM event_reactions WHERE event_id = e.id AND user_id = %s) as user_liked
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    JOIN locations l ON e.location_id = l.id
    WHERE j.user_id = %s
    """
    params = [user_id, user_id]
    if only_public:
        query += " AND j.is_public = TRUE AND j.is_hidden = FALSE"
    query += " ORDER BY e.start_datetime DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])
    print(f"Debug - Querying events for user_id: {user_id}, page: {page}, per_page: {per_page}, only_public: {only_public}")
    events = db.query_db(query, params, fetch_all=True)
    print(f"Debug - Found {len(events) if events else 0} events")
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page
    print(f"Debug - Total events: {total}, Total pages: {total_pages}")
    print(f"Debug - Executed SQL: {query}")
    return events, total, total_pages

def get_user_visited_places(user_id):
    """Get places visited by user (based on event table)"""
    query = """
    SELECT DISTINCT 
        l.id,
        l.name,
        COUNT(DISTINCT e.id) as visit_count
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    JOIN locations l ON e.location_id = l.id
    WHERE j.user_id = %s
    AND j.is_public = TRUE
    AND j.is_hidden = FALSE
    GROUP BY l.id, l.name
    ORDER BY visit_count DESC
    LIMIT 10
    """
    return db.query_db(query, (user_id,), fetch_all=True)

def get_help_requests(user_type='all', page=1, per_page=10):
    """
    Get a list of help requests, supporting filtering by user type
    """
    # Basic query
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        hr.*,
        u.username,
        u.first_name,
        u.last_name,
        u.role,
        u.profile_image,
        CASE 
            WHEN u.role IN ('admin', 'editor', 'support_techs') THEN 'staff'
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = u.id 
                AND us.end_date > NOW()
            ) THEN 'premium'
            ELSE 'free'
        END as user_type,
        (
            SELECT COUNT(*) 
            FROM help_request_replies 
            WHERE request_id = hr.id
        ) as reply_count
    FROM help_requests hr
    JOIN users u ON hr.user_id = u.id
    WHERE 1=1
    """
    params = []

    # Filter by user type
    if user_type != 'all':
        if user_type == 'premium':
            query += """ AND EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = u.id 
                AND us.end_date > NOW()
            )"""
        elif user_type == 'staff':
            query += " AND u.role IN ('admin', 'editor', 'support_techs')"
        elif user_type == 'free':
            query += """ AND u.role = 'traveller' 
                AND NOT EXISTS (
                    SELECT 1 FROM user_subscriptions us 
                    WHERE us.user_id = u.id 
                    AND us.end_date > NOW()
                )"""

    # Sort by priority and submission time
    query += """ ORDER BY 
        CASE 
            WHEN u.role IN ('admin', 'editor', 'support_techs') THEN 1
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = u.id 
                AND us.end_date > NOW()
            ) THEN 2
            ELSE 3
        END,
        hr.created_at DESC
    """

    # pagenation
    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    # get request list
    requests = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return {
        'requests': requests,
        'total': total,
        'total_pages': total_pages
    }

def create_help_request(user_id, title, content, category, attachments=None, bug_data=None):
    """
    create new help request
    """
    # Start transaction
    db.begin_transaction()
    try:
        # Create a help request
        query = """
        INSERT INTO help_requests (user_id, title, content, category)
        VALUES (%s, %s, %s, %s)
        """
        request_id = db.execute_db(query, (user_id, title, content, category))
        
        # Save attachment
        if attachments:
            for attachment in attachments:
                query = """
                INSERT INTO help_request_attachments (request_id, file_name, file_path)
                VALUES (%s, %s, %s)
                """
                db.execute_db(query, (request_id, attachment, attachment))
        
        # Save bug report data
        if category == 'bug' and bug_data:
            query = """
            INSERT INTO help_request_bug_data (request_id, steps, expected_behavior, actual_behavior)
            VALUES (%s, %s, %s, %s)
            """
            db.execute_db(query, (
                request_id,
                bug_data.get('steps'),
                bug_data.get('expected_behavior'),
                bug_data.get('actual_behavior')
            ))
        
        # Commit transaction
        db.commit_transaction()
        return request_id
    except Exception as e:
        # Rollback transaction.
        db.rollback_transaction()
        raise e

def get_help_request_by_id(request_id):
    """
    获取帮助请求详情
    """
    # Get basic request information
    query = """
    SELECT 
        hr.*,
        u.username,
        u.first_name,
        u.last_name,
        u.role,
        u.profile_image,
        CASE 
            WHEN u.role IN ('admin', 'editor', 'support_techs') THEN 'staff'
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = u.id 
                AND us.end_date > NOW()
            ) THEN 'premium'
            ELSE 'free'
        END as user_type,
        (
            SELECT COUNT(*) 
            FROM help_request_replies 
            WHERE request_id = hr.id
        ) as reply_count
    FROM help_requests hr
    JOIN users u ON hr.user_id = u.id
    WHERE hr.id = %s
    """
    help_request = db.query_db(query, (request_id,), fetch_one=True)
    
    if not help_request:
        return None
    
    # get attachment
    query = """
    SELECT file_name, file_path
    FROM help_request_attachments
    WHERE request_id = %s
    """
    attachments = db.query_db(query, (request_id,), fetch_all=True)
    help_request['attachments'] = attachments or []
    
    # get reply
    query = """
    SELECT 
        hrr.*,
        u.username,
        u.first_name,
        u.last_name,
        u.role,
        u.profile_image
    FROM help_request_replies hrr
    JOIN users u ON hrr.user_id = u.id
    WHERE hrr.request_id = %s
    ORDER BY hrr.created_at ASC
    """
    replies = db.query_db(query, (request_id,), fetch_all=True)
    help_request['replies'] = replies or []
    
    # If it is a bug report, get the bug report data
    if help_request['category'] == 'bug':
        query = """
        SELECT steps, expected_behavior, actual_behavior
        FROM help_request_bug_data
        WHERE request_id = %s
        """
        bug_data = db.query_db(query, (request_id,), fetch_one=True)
        help_request['bug_data'] = bug_data or {}
    
    return help_request

def create_help_request_reply(request_id, user_id, content):
    """
    Create a help request reply
    """
    query = """
    INSERT INTO help_request_replies (request_id, user_id, content)
    VALUES (%s, %s, %s)
    """
    return db.execute_db(query, (request_id, user_id, content))

def get_help_request_replies(request_id):
    """
    Get all replies to the help request
    """
    query = """
    SELECT 
        hrr.*,
        u.username,
        u.first_name,
        u.last_name,
        u.role,
        u.profile_image
    FROM help_request_replies hrr
    JOIN users u ON hrr.user_id = u.id
    WHERE hrr.request_id = %s
    ORDER BY hrr.created_at ASC
    """
    return db.query_db(query, (request_id,), fetch_all=True)

def get_staff_members():
    """
    get all staffs（Editor, Admin, Support Tech）
    """
    query = """
    SELECT id, username, first_name, last_name, role
    FROM users
    WHERE role IN ('editor', 'admin', 'support_techs')
    AND status = 'active'
    ORDER BY role, first_name, last_name
    """
    return db.query_db(query, fetch_all=True)

def get_help_requests_for_staff(user_type='all', page=1, per_page=10, status=None, assigned_to=None):
    """
    Get a list of help requests, supporting filtering by user type, status, and assignee
    """
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        hr.*,
        u.username,
        u.first_name,
        u.last_name,
        u.role,
        u.profile_image,
        CASE 
            WHEN u.role IN ('admin', 'editor', 'support_techs') THEN 'staff'
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = u.id 
                AND us.end_date > NOW()
            ) THEN 'premium'
            ELSE 'free'
        END as user_type,
        (
            SELECT COUNT(*) 
            FROM help_request_replies 
            WHERE request_id = hr.id
        ) as reply_count,
        a.username as assigned_username,
        a.first_name as assigned_first_name,
        a.last_name as assigned_last_name,
        a.role as assigned_role
    FROM help_requests hr
    JOIN users u ON hr.user_id = u.id
    LEFT JOIN users a ON hr.assigned_to = a.id
    WHERE 1=1
    """
    params = []

    # Filter by user type
    if user_type != 'all':
        if user_type == 'premium':
            query += """ AND EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = u.id 
                AND us.end_date > NOW()
            )"""
        elif user_type == 'staff':
            query += " AND u.role IN ('admin', 'editor', 'support_techs')"
        elif user_type == 'free':
            query += """ AND u.role = 'traveller' 
                AND NOT EXISTS (
                    SELECT 1 FROM user_subscriptions us 
                    WHERE us.user_id = u.id 
                    AND us.end_date > NOW()
                )"""

    # Filter by status
    if status:
        query += " AND hr.status = %s"
        params.append(status)

    # Filter by assignee
    if assigned_to:
        query += " AND hr.assigned_to = %s"
        params.append(assigned_to)

    # Sort by priority and submission time
    query += """ ORDER BY 
        CASE 
            WHEN hr.status = 'new' THEN 1
            WHEN hr.status = 'in_progress' THEN 2
            WHEN hr.status = 'on_hold' THEN 3
            ELSE 4
        END,
        hr.created_at DESC
    """

    # pagenation
    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    # get request list
    requests = db.query_db(query, params, fetch_all=True)

    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page

    return {
        'requests': requests,
        'total': total,
        'total_pages': total_pages
    }

def assign_help_request(request_id, staff_id):
    """
    Assign a help request to staff
    """
    query = """
    UPDATE help_requests 
    SET assigned_to = %s,
        assigned_at = CURRENT_TIMESTAMP,
        abandoned_at = NULL,
        updated_at = NOW()
    WHERE id = %s
    """
    return db.execute_db(query, (staff_id, request_id))

def abandon_help_request(request_id):
    """
    Abandon processing help requests
    """
    query = """
    UPDATE help_requests 
    SET assigned_to = NULL,
        assigned_at = NULL,
        abandoned_at = CURRENT_TIMESTAMP,
        updated_at = NOW()
    WHERE id = %s
    """
    return db.execute_db(query, (request_id,))

def update_help_request_status(request_id, status, hold_reason=None, resolution_summary=None):
    """
    Update help request status
    Args:
        request_id: Request ID
        status: New status (new, in_progress, on_hold, resolved)
        hold_reason: Reason for putting request on hold
        resolution_summary: Summary of resolution
    """
    # Validate status
    valid_statuses = ['new', 'in_progress', 'on_hold', 'resolved']
    if status not in valid_statuses:
        raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')

    # Build update query
    query = """
        UPDATE help_requests 
        SET status = %s,
            hold_reason = %s,
            resolution_summary = %s,
            updated_at = NOW()
        WHERE id = %s
    """
    params = [status, hold_reason, resolution_summary, request_id]

    # Execute update
    try:
        db.execute_db(query, params)
    except Exception as e:
        raise Exception(f'Error updating help request status: {str(e)}')

def get_user_help_requests(user_id, status='all', page=1, per_page=10):
    """Get list of help requests submitted by a user
    
    Args:
        user_id: User ID
        status: Request status filter (all, new, in_progress, on_hold, resolved)
        page: Page number
        per_page: Number of items per page
        
    Returns:
        Dictionary containing requests list and total pages
    """
    try:
        # Build query
        query = """
            SELECT SQL_CALC_FOUND_ROWS 
                hr.*,
                u.first_name as assigned_first_name,
                u.last_name as assigned_last_name,
                (SELECT COUNT(*) FROM help_request_replies WHERE request_id = hr.id) as reply_count
            FROM help_requests hr
            LEFT JOIN users u ON hr.assigned_to = u.id
            WHERE hr.user_id = %s
        """
        params = [user_id]

        # Add status filter
        if status != 'all':
            query += " AND hr.status = %s"
            params.append(status)

        # Add order and limit
        query += " ORDER BY hr.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, (page - 1) * per_page])

        # Debug print
        print(f"Debug - Executing query: {query}")
        print(f"Debug - Query params: {params}")

        # Execute query with fetch_all=True to ensure all results are read
        requests = db.query_db(query, params, fetch_all=True)
        print(f"Debug - Query result: {requests}")

        # Get total records with fetch_one=True
        total_query = "SELECT FOUND_ROWS() as total"
        total_result = db.query_db(total_query, fetch_one=True)
        total = total_result['total'] if total_result else 0
        print(f"Debug - Total records: {total}")

        # Format results
        if requests:
            for request in requests:
                # Format dates
                if 'created_at' in request:
                    request['created_at'] = request['created_at'].strftime('%Y-%m-%d %H:%M')
                if 'updated_at' in request:
                    request['updated_at'] = request['updated_at'].strftime('%Y-%m-%d %H:%M')

        return {
            'requests': requests or [],
            'total_pages': (total + per_page - 1) // per_page
        }

    except Exception as e:
        print(f"Error in get_user_help_requests: {str(e)}")
        return {'requests': [], 'total_pages': 0}

def check_journey_follow_status(journey_id, user_id):
    """
    Check if the user has followed a journey
    """
    query = """
    SELECT 1 FROM follows 
    WHERE follower_id = %s 
    AND followed_type = 'journey' 
    AND followed_id = %s
    """
    result = db.query_db(query, (user_id, journey_id), fetch_one=True)
    return bool(result)

def toggle_journey_follow(journey_id, user_id):
    """
    Toggle the follow status of the journey.
    Returns: True if followed, False if unfollowed.
    """
    # Check current follow status
    is_following = check_journey_follow_status(journey_id, user_id)
    
    if is_following:
        # If already followed, unfollow
        query = """
        DELETE FROM follows 
        WHERE follower_id = %s 
        AND followed_type = 'journey' 
        AND followed_id = %s
        """
        db.execute_db(query, (user_id, journey_id))
        return False
    else:
        # If not followed, add to follow
        query = """
        INSERT INTO follows (follower_id, followed_type, followed_id)
        VALUES (%s, 'journey', %s)
        """
        db.execute_db(query, (user_id, journey_id))
        return True

def check_user_follow_status(user_id, follower_id):
    """
    Check if the user is following another user
    """
    query = """
    SELECT 1 FROM follows 
    WHERE follower_id = %s 
    AND followed_type = 'user' 
    AND followed_id = %s
    """
    result = db.query_db(query, (follower_id, user_id), fetch_one=True)
    return bool(result)

def toggle_user_follow(user_id, follower_id):
    """
    Toggle user follow status.
    Returns: True if followed, False if unfollowed.
    """
    # Check current follow status
    is_following = check_user_follow_status(user_id, follower_id)
    
    if is_following:
        # If already followed, unfollow
        query = """
        DELETE FROM follows 
        WHERE follower_id = %s 
        AND followed_type = 'user' 
        AND followed_id = %s
        """
        db.execute_db(query, (follower_id, user_id))
        return False
    else:
        # If not followed, add to follow
        query = """
        INSERT INTO follows (follower_id, followed_type, followed_id)
        VALUES (%s, 'user', %s)
        """
        db.execute_db(query, (follower_id, user_id))
        return True

def get_followed_users_journeys(follower_id, current_page, per_page):
    """
    Get public journeys of all users that the user follows, and journeys directly followed by the user.
    Condition: public journeys from users followed by the user OR public journeys directly followed by the user.
    """
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        j.*,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        CASE 
            WHEN u.role IN ('admin', 'editor') THEN TRUE
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = j.user_id 
                AND us.end_date > NOW()
            ) THEN TRUE
            ELSE FALSE
        END as has_active_subscription,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo,
        TRUE as is_following
    FROM journeys j
    LEFT JOIN users u ON j.user_id = u.id
    WHERE j.is_published = TRUE 
    AND j.is_hidden = FALSE
    AND (
        -- Get public journeys published by users the user follows
        EXISTS (
            SELECT 1 
            FROM follows f 
            WHERE f.follower_id = %s 
            AND f.followed_type = 'user' 
            AND f.followed_id = j.user_id
        )
        OR 
        -- Get journeys directly followed by the user.
        EXISTS (
            SELECT 1 
            FROM follows f 
            WHERE f.follower_id = %s 
            AND f.followed_type = 'journey' 
            AND f.followed_id = j.id
        )
    )
    ORDER BY j.start_date DESC, j.created_at DESC 
    LIMIT %s OFFSET %s
    """
    params = [follower_id, follower_id, per_page, (current_page - 1) * per_page]
    
    # Get a list of journeys
    journeys = db.query_db(query, params, fetch_all=True)
    
    # Get total count
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page
    
    return journeys, total, total_pages

def get_followed_journeys_events(follower_id, current_page, per_page):
    """
    Get the list of events for journeys directly followed by the user
    """
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        e.*,
        j.title as journey_title,
        j.is_public as journey_is_public,
        j.is_hidden as journey_is_hidden,
        u.id as user_id,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        l.name as location_name,
        CASE 
            WHEN u.role IN ('admin', 'editor') THEN TRUE
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = j.user_id 
                AND us.end_date > NOW()
            ) THEN TRUE
            ELSE FALSE
        END as has_active_subscription,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo,
        TRUE as is_following,
        (SELECT COUNT(*) FROM event_reactions WHERE event_id = e.id) as like_count,
        (SELECT COUNT(*) FROM comments WHERE event_id = e.id) as comment_count,
        EXISTS (
            SELECT 1 FROM event_reactions 
            WHERE event_id = e.id AND user_id = %s
        ) as user_liked,
        GROUP_CONCAT(p.photo_url) as photo_urls
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    LEFT JOIN users u ON j.user_id = u.id
    LEFT JOIN locations l ON e.location_id = l.id
    LEFT JOIN photos p ON e.id = p.event_id
    WHERE j.is_published = TRUE 
    AND j.is_hidden = FALSE
    AND EXISTS (
        SELECT 1 
        FROM follows f 
        WHERE f.follower_id = %s 
        AND f.followed_type = 'journey' 
        AND f.followed_id = j.id
    )
    GROUP BY e.id, j.title, j.is_public, j.is_hidden, u.id, u.first_name, u.last_name, u.profile_image, u.role, l.name
    ORDER BY e.start_datetime DESC, e.created_at DESC 
    LIMIT %s OFFSET %s
    """
    params = [follower_id, follower_id, per_page, (current_page - 1) * per_page]
    
    # get events list
    events = db.query_db(query, params, fetch_all=True)
    
    # get total count
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page
    
    return events, total, total_pages

def get_followed_users_journeys_events(follower_id, current_page, per_page):
    """
    Get a list of events for journeys published by users the user follows.
    As long as the user follows the publisher, and the journey is public and not hidden, all events can be seen.
    """
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        e.*,
        j.title as journey_title,
        j.is_public as journey_is_public,
        j.is_hidden as journey_is_hidden,
        u.id as user_id,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        l.name as location_name,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo,
        TRUE as is_following,
        (SELECT COUNT(*) FROM event_reactions WHERE event_id = e.id) as like_count,
        (SELECT COUNT(*) FROM comments WHERE event_id = e.id) as comment_count,
        EXISTS (
            SELECT 1 FROM event_reactions 
            WHERE event_id = e.id AND user_id = %s
        ) as user_liked,
        GROUP_CONCAT(p.photo_url) as photo_urls
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    JOIN users u ON j.user_id = u.id
    LEFT JOIN locations l ON e.location_id = l.id
    LEFT JOIN photos p ON e.id = p.event_id
    JOIN follows f ON f.followed_id = u.id AND f.followed_type = 'user'
    WHERE f.follower_id = %s
    AND j.is_public = TRUE 
    AND j.is_hidden = FALSE
    GROUP BY e.id, j.title, j.is_public, j.is_hidden, u.id, u.first_name, u.last_name, u.profile_image, u.role, l.name
    ORDER BY e.start_datetime DESC, e.created_at DESC 
    LIMIT %s OFFSET %s
    """
    params = [follower_id, follower_id, per_page, (current_page - 1) * per_page]
    
    # get events list
    events = db.query_db(query, params, fetch_all=True)
    
    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page
    
    return events, total, total_pages

def is_premiun_user(user_id):
    """get journeys page"""
    query = """
    SELECT * FROM user_subscriptions WHERE user_id = %s AND end_date > NOW(); 
    """

    # get subscription
    subscriptions = db.query_db(query, (user_id,), fetch_all=True)
    return len(subscriptions) > 0

def get_followed_locations_events(user_id, current_page, per_page):
    """
    Get a list of events related to locations followed by the user
    """
    query = """
    SELECT SQL_CALC_FOUND_ROWS 
        e.*,
        j.title as journey_title,
        j.is_public as journey_is_public,
        j.is_hidden as journey_is_hidden,
        u.id as user_id,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.role,
        l.name as location_name,
        CASE 
            WHEN u.role IN ('admin', 'editor') THEN TRUE
            WHEN EXISTS (
                SELECT 1 FROM user_subscriptions us 
                WHERE us.user_id = j.user_id 
                AND us.end_date > NOW()
            ) THEN TRUE
            ELSE FALSE
        END as has_active_subscription,
        (SELECT photo_url FROM covers WHERE journey_id = j.id LIMIT 1) as cover_photo,
        TRUE as is_following,
        (SELECT COUNT(*) FROM event_reactions WHERE event_id = e.id) as like_count,
        (SELECT COUNT(*) FROM comments WHERE event_id = e.id) as comment_count,
        EXISTS (
            SELECT 1 FROM event_reactions 
            WHERE event_id = e.id AND user_id = %s
        ) as user_liked,
        GROUP_CONCAT(p.photo_url) as photo_urls
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    LEFT JOIN users u ON j.user_id = u.id
    JOIN locations l ON e.location_id = l.id
    LEFT JOIN photos p ON e.id = p.event_id
    WHERE j.is_public = TRUE 
    AND j.is_hidden = FALSE
    AND EXISTS (
        SELECT 1 
        FROM follows f 
        WHERE f.follower_id = %s 
        AND f.followed_type = 'location' 
        AND f.followed_id = l.id
    )
    GROUP BY e.id, j.title, j.is_public, j.is_hidden, u.id, u.first_name, u.last_name, u.profile_image, u.role, l.name
    ORDER BY e.start_datetime DESC, e.created_at DESC 
    LIMIT %s OFFSET %s
    """
    params = [user_id, user_id, per_page, (current_page - 1) * per_page]
    
    # get events list
    events = db.query_db(query, params, fetch_all=True)
    
    # get total
    total_query = "SELECT FOUND_ROWS() AS total"
    total = db.query_db(total_query, fetch_one=True)["total"]
    total_pages = (total + per_page - 1) // per_page
    
    return events, total, total_pages

def get_followed_users(user_id):
    """Get a list of users followed by the user"""
    query = """
        SELECT u.id, u.username, u.first_name, u.last_name, u.profile_image, u.description,
               l.name as location_name
        FROM follows f
        JOIN users u ON f.followed_id = u.id
        LEFT JOIN locations l ON u.location_id = l.id
        WHERE f.follower_id = %s AND f.followed_type = 'user'
        ORDER BY f.created_at DESC
    """
    return db.query_db(query, (user_id,), fetch_all=True)

def get_followed_locations(user_id):
    """Get a list of locations followed by the user"""
    query = """
        SELECT l.id, l.name, 
               (SELECT COUNT(*) FROM follows WHERE followed_id = l.id AND followed_type = 'location') as follower_count
        FROM follows f
        JOIN locations l ON f.followed_id = l.id
        WHERE f.follower_id = %s AND f.followed_type = 'location'
        ORDER BY f.created_at DESC
    """
    return db.query_db(query, (user_id,), fetch_all=True)

def is_following_location(user_id, location_id):
    """
    Check if the user has followed a location
    """
    query = """
    SELECT 1 FROM follows 
    WHERE follower_id = %s 
    AND followed_type = 'location' 
    AND followed_id = %s
    """
    result = db.query_db(query, (user_id, location_id), fetch_one=True)
    return bool(result)

def follow_location(user_id, location_id):
    """
    follow a location
    """
    query = """
    INSERT INTO follows (follower_id, followed_type, followed_id)
    VALUES (%s, 'location', %s)
    """
    return db.execute_db(query, (user_id, location_id))

def unfollow_location(user_id, location_id):
    """
    unfollow a location
    """
    query = """
    DELETE FROM follows 
    WHERE follower_id = %s 
    AND followed_type = 'location' 
    AND followed_id = %s
    """
    return db.execute_db(query, (user_id, location_id))

def get_followed_journeys_events_count(user_id):
    """
    Get the number of events for journeys directly followed by the user
    """
    query = """
    SELECT COUNT(*) as count
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    WHERE j.is_public = TRUE 
    AND j.is_hidden = FALSE
    AND EXISTS (
        SELECT 1 
        FROM follows f 
        WHERE f.follower_id = %s 
        AND f.followed_type = 'journey' 
        AND f.followed_id = j.id
    )
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0

def get_followed_users_journeys_events_count(user_id):
    """
    Get the number of events for journeys published by users the user follows
    """
    query = """
    SELECT COUNT(*) as count
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    WHERE j.is_public = TRUE 
    AND j.is_hidden = FALSE
    AND EXISTS (
        SELECT 1 
        FROM follows f 
        WHERE f.follower_id = %s 
        AND f.followed_type = 'user' 
        AND f.followed_id = j.user_id
    )
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0

def get_followed_locations_events_count(user_id):
    """
    Get the number of events related to locations followed by the user.
    """
    query = """
    SELECT COUNT(*) as count
    FROM events e
    JOIN journeys j ON e.journey_id = j.id
    JOIN locations l ON e.location_id = l.id
    WHERE j.is_public = TRUE 
    AND j.is_hidden = FALSE
    AND EXISTS (
        SELECT 1 
        FROM follows f 
        WHERE f.follower_id = %s 
        AND f.followed_type = 'location' 
        AND f.followed_id = l.id
    )
    """
    result = db.query_db(query, (user_id,), fetch_one=True)
    return result['count'] if result else 0

def record_edit_history(journey_id, event_id, editor_id, edit_type, edit_reason, edit_content=None):
    """
    Record edit history
    """
    if journey_id and event_id:
        raise ValueError("journey_id and event_id can not be together")
    if not journey_id and not event_id:
        raise ValueError("journey_id or event_id is needed")
    if edit_type not in ['text', 'image', 'location']:
        raise ValueError("edit_type must be on of 'text', 'image', 'location' ")

    query = """
    INSERT INTO edit_history (journey_id, event_id, editor_id, edit_type, edit_reason, edit_content)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    return db.execute_db(query, (
        journey_id, 
        event_id, 
        editor_id, 
        edit_type, 
        edit_reason, 
        json.dumps(edit_content, default=_json_serial) if edit_content else None
    ))

def get_journey_edit_history(journey_id):
    """
    Get the edit history of the journey.
    """
    query = """
    SELECT 
        eh.id,
        eh.journey_id,
        eh.event_id,
        eh.edit_type,
        eh.edit_reason,
        eh.edit_content,
        eh.created_at,
        u.first_name,
        u.last_name,
        u.profile_image
    FROM edit_history eh
    LEFT JOIN users u ON eh.editor_id = u.id
    WHERE eh.journey_id = %s
    ORDER BY eh.created_at DESC
    """
    try:
        results = db.query_db(query, (journey_id,), fetch_all=True)
        for result in results:
            if result['edit_content']:
                result['edit_content'] = json.loads(result['edit_content'])
        return results if results else []
    except Exception as e:
        print(f"Error getting journey edit history: {str(e)}")
        return []

def get_event_edit_history(event_id):
    """
    Get the edit history of the journey.
    """
    query = """
    SELECT 
        eh.id,
        eh.journey_id,
        eh.event_id,
        eh.edit_type,
        eh.edit_reason,
        eh.edit_content,
        eh.created_at,
        u.first_name,
        u.last_name,
        u.profile_image,
        u.id as user_id
    FROM edit_history eh
    LEFT JOIN users u ON eh.editor_id = u.id
    WHERE eh.event_id = %s
    ORDER BY eh.created_at DESC
    """
    try:
        results = db.query_db(query, (event_id,), fetch_all=True)
        for result in results:
            if result['edit_content']:
                result['edit_content'] = json.loads(result['edit_content'])
        return results if results else []
    except Exception as e:
        print(f"Error getting event edit history: {str(e)}")
        return []

def get_all_edit_history(page=1, per_page=10, editor_id=None, edit_type=None):
    """
    Get all edit history records, only including records where the editor is not the journey owner.
    """
    try:
        offset = (page - 1) * per_page
        
        # Build a basic query
        query = """
            SELECT eh.*, 
                   u.username as editor_username,
                   j.title as journey_title,
                   j.user_id as journey_owner_id,
                   owner.username as journey_owner_username,
                   e.title as event_title
            FROM edit_history eh
            INNER JOIN users u ON eh.editor_id = u.id
            LEFT JOIN journeys j ON eh.journey_id = j.id
            LEFT JOIN users owner ON j.user_id = owner.id
            LEFT JOIN events e ON eh.event_id = e.id
            WHERE (eh.journey_id IS NULL OR eh.editor_id != j.user_id)
        """
        count_query = """
            SELECT COUNT(*) as total
            FROM edit_history eh
            INNER JOIN users u ON eh.editor_id = u.id
            LEFT JOIN journeys j ON eh.journey_id = j.id
            WHERE (eh.journey_id IS NULL OR eh.editor_id != j.user_id)
        """
        
        params = []
        
        # Add filter conditions
        if editor_id:
            query += " AND eh.editor_id = %s"
            count_query += " AND eh.editor_id = %s"
            params.append(editor_id)
        
        if edit_type:
            query += " AND eh.edit_type = %s"
            count_query += " AND eh.edit_type = %s"
            params.append(edit_type)
        
        # Add sorting and pagination
        query += " ORDER BY eh.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        edit_history = db.query_db(query, params)
        total = db.query_db(count_query, params[:-2])[0]['total'] 
        total_pages = (total + per_page - 1) // per_page
        
        return edit_history, total, total_pages
    except Exception as e:
        print(f"Error getting edit history: {str(e)}")
        return [], 0, 0

def get_system_user():
    """
    Get system user information
    """
    return {
        'id': 0,
        'username': 'System',
        'first_name': 'Official',
        'last_name': 'System',
        'profile_image': None
    }

def create_appeal(user_id, appeal_type, content, journey_id=None):
    """
    create appeal
    """
    sql = """
        INSERT INTO appeals (user_id, appeal_type, content, status, journey_id)
        VALUES (%s, %s, %s, 'pending', %s)
    """
    return db.execute_db(sql, (user_id, appeal_type, content, journey_id))

def get_appeals(page=1, per_page=10, status=None):
    """
    get appeal
    """
    try:
        offset = (page - 1) * per_page
        params = []
        
        base_sql = """
            SELECT 
                a.*,
                u.username,
                u.first_name,
                u.last_name,
                u.profile_image,
                CASE 
                    WHEN a.appeal_type = 'hidden_journey' THEN j.title
                    ELSE NULL
                END as journey_title
            FROM appeals a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN journeys j ON a.journey_id = j.id
            WHERE 1=1
        """
        
        # Add status filtering
        if status:
            base_sql += " AND a.status = %s"
            params.append(status)
            
        # Add sorting and pagination
        base_sql += " ORDER BY a.created_at DESC LIMIT %s OFFSET %s"
        params.extend([per_page, offset])
        
        appeals = db.query_db(base_sql, params, fetch_all=True)
        
        # get total
        count_sql = "SELECT COUNT(*) as total FROM appeals"
        count_params = []
        if status:
            count_sql += " WHERE status = %s"
            count_params.append(status)
            total = db.query_db(count_sql, count_params, fetch_one=True)["total"]
        else:
            total = db.query_db(count_sql, None, fetch_one=True)["total"]
            
        return appeals, total
    except Exception as e:
        print(f"Error getting appeals: {str(e)}")
        return [], 0

def get_appeal_by_id(appeal_id):
    """
    get appeal detail
    """
    try:
        sql = """
            SELECT 
                a.*,
                u.username,
                u.first_name,
                u.last_name,
                u.profile_image,
                CASE 
                    WHEN a.appeal_type = 'hidden_journey' THEN j.title
                    ELSE NULL
                END as journey_title
            FROM appeals a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN journeys j ON a.journey_id = j.id
            WHERE a.id = %s
        """
        appeal = db.query_db(sql, (appeal_id,), fetch_one=True)
        
        if appeal and appeal['appeal_type'] == 'hidden_journey':
            # Get relevant journey details
            journey_sql = """
                SELECT 
                    j.*,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.profile_image
                FROM journeys j
                LEFT JOIN users u ON j.user_id = u.id
                WHERE j.id = %s
            """
            journey = db.query_db(journey_sql, (appeal['journey_id'],), fetch_one=True)
            if journey:
                appeal['journey'] = journey
                
        return appeal
    except Exception as e:
        print(f"Error getting appeal: {str(e)}")
        return None

def update_appeal_status(appeal_id, status):
    """
    update appeal status
    """
    try:
        sql = """
            UPDATE appeals 
            SET 
                status = %s
            WHERE id = %s
        """
        db.execute_db(sql, (status, appeal_id))
        return True
    except Exception as e:
        print(f"Error updating appeal status: {str(e)}")
        return False

def get_user_appeals(user_id, page=1, per_page=10):
    """
    get appeal list
    """
    try:
        offset = (page - 1) * per_page
        
        sql = """
            SELECT 
                a.*,
                u.username,
                u.first_name,
                u.last_name,
                u.profile_image,
                CASE 
                    WHEN a.appeal_type = 'hidden_journey' THEN j.title
                    ELSE NULL
                END as journey_title
            FROM appeals a
            LEFT JOIN users u ON a.user_id = u.id
            LEFT JOIN journeys j ON a.journey_id = j.id
            WHERE a.user_id = %s
            ORDER BY a.created_at DESC
            LIMIT %s OFFSET %s
        """
        appeals = db.query_db(sql, (user_id, per_page, offset), fetch_all=True)
        
        # get total
        count_sql = "SELECT COUNT(*) as total FROM appeals WHERE user_id = %s"
        total = db.query_db(count_sql, (user_id,), fetch_one=True)["total"]
        
        return appeals, total
    except Exception as e:
        print(f"Error getting user appeals: {str(e)}")
        return [], 0