DROP DATABASE IF EXISTS travel_journal;
CREATE DATABASE travel_journal;
USE travel_journal;

-- Drop tables in the correct order to avoid FK issues
DROP TABLE IF EXISTS moderation;
DROP TABLE IF EXISTS announcements;
DROP TABLE IF EXISTS photos;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS journeys;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS locations;

--  Locations table
CREATE TABLE locations
(
    id   INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE
);

-- Users table with role as ENUM
CREATE TABLE users
(
    id            INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)                           NOT NULL UNIQUE,
    email         VARCHAR(100)                          NOT NULL UNIQUE,
    password_hash VARCHAR(255)                          NOT NULL,
    first_name    VARCHAR(50),
    last_name     VARCHAR(50),
    location_id   INT,
    description   TEXT,
    profile_image VARCHAR(255),
    role          ENUM ('traveller', 'editor', 'admin', 'moderator', 'support_techs') NOT NULL DEFAULT 'traveller',
    status        ENUM ('active', 'banned')           NOT NULL DEFAULT 'active',
    can_share     BOOLEAN                                        DEFAULT TRUE,
    can_publish  BOOLEAN  DEFAULT FALSE,
    is_public_profile BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
);

-- Journeys table
CREATE TABLE journeys
(
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT          NOT NULL,
    title        VARCHAR(255) NOT NULL,
    description  TEXT,
    start_date   DATE         NOT NULL,
    is_public    BOOLEAN   DEFAULT FALSE,
    is_hidden    BOOLEAN   DEFAULT FALSE,
    is_published BOOLEAN   DEFAULT FALSE,
    no_edit      BOOLEAN   DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Events table (created before photos to avoid FK issue)
CREATE TABLE events
(
    id             INT AUTO_INCREMENT PRIMARY KEY,
    journey_id     INT          NOT NULL,
    title          VARCHAR(255) NOT NULL,
    description    TEXT,
    start_datetime DATETIME     NOT NULL,
    end_datetime   DATETIME DEFAULT NULL,
    location_id    INT          NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (journey_id) REFERENCES journeys (id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
);

-- Photos table (with event_id column to link each photo to an event)
CREATE TABLE photos
(
    id        INT AUTO_INCREMENT PRIMARY KEY,
    photo_url VARCHAR(255) NOT NULL,
    event_id  INT          NOT NULL, -- New column to associate a photo with an event
    display_order  INT     NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
);

-- Covers table (with journey_id column to link each cover to an journey)
CREATE TABLE covers
(
    id        INT AUTO_INCREMENT PRIMARY KEY,
    photo_url VARCHAR(255) NOT NULL,
    journey_id  INT          NOT NULL, -- New column to associate a photo with a journey
    FOREIGN KEY (journey_id) REFERENCES journeys (id) ON DELETE CASCADE
);

-- Announcements table
CREATE TABLE announcements
(
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT          NOT NULL,
    title      VARCHAR(255) NOT NULL,
    content    TEXT         NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Admins and Editors moderating public content
CREATE TABLE moderation
(
    id           INT AUTO_INCREMENT PRIMARY KEY,
    moderator_id INT                             NOT NULL,
    journey_id   INT,
    event_id     INT,
    action       ENUM ('edit', 'hide', 'delete') NOT NULL,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (moderator_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (journey_id) REFERENCES journeys (id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
);

-- ========== Drop and Create new tables ==========

-- Stores all available subscription plans and their pricing
DROP TABLE IF EXISTS subscription_plans;
CREATE TABLE subscription_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,  -- 'Free Trial', 'One Month', 'One Quarter', 'One Year'
    months INT NOT NULL,        -- 0 for Free Trial, 1, 3, 12
    price_nz DECIMAL(10,2) NOT NULL,  -- Price including GST
    price_other DECIMAL(10,2) NOT NULL, -- Price excluding GST
    discount DECIMAL(5,2) DEFAULT NULL -- Discount percentage, e.g. 10.00 means 10% off
);

-- Records all user subscription purchases, trials, and admin grants
DROP TABLE IF EXISTS user_subscriptions;
CREATE TABLE user_subscriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    plan_id INT NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    payment_amount DECIMAL(10,2) NOT NULL,
    gst_amount DECIMAL(10,2) DEFAULT 0,
    billing_country VARCHAR(100) NOT NULL,
    is_free_trial BOOLEAN DEFAULT FALSE,
    granted_by_admin BOOLEAN DEFAULT FALSE, -- True if granted by admin, not purchased
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES subscription_plans(id),
    UNIQUE KEY unique_free_trial (user_id, is_free_trial)
);

-- Stores likes for events
DROP TABLE IF EXISTS event_reactions;
CREATE TABLE event_reactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    reaction_type ENUM('like') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_event_reaction (event_id, user_id)
);

-- Stores comments posted by users on events
DROP TABLE IF EXISTS comments;
CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_hidden BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores likes and dislikes for comments
DROP TABLE IF EXISTS comment_reactions;
CREATE TABLE comment_reactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comment_id INT NOT NULL,
    user_id INT NOT NULL,
    reaction_type ENUM('like', 'dislike') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_reaction (comment_id, user_id)
);

-- Stores reports of abusive, offensive, or spam comments
DROP TABLE IF EXISTS comment_reports;
CREATE TABLE comment_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    comment_id INT NOT NULL,
    reporter_id INT NOT NULL,
    report_type ENUM('abusive', 'offensive', 'spam') NOT NULL,
    content TEXT NOT NULL,
    status ENUM('pending', 'reviewed', 'resolved') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE,
    FOREIGN KEY (reporter_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores private messages exchanged between users
DROP TABLE IF EXISTS private_messages;
CREATE TABLE private_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores all available achievements for gamification
DROP TABLE IF EXISTS achievements;
CREATE TABLE achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Records which achievements each user has earned
DROP TABLE IF EXISTS user_achievements;
CREATE TABLE user_achievements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    achievement_id INT NOT NULL,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
    UNIQUE KEY unique_achievement (user_id, achievement_id)
);

-- Stores follow relationships for journeys, users, and locations
DROP TABLE IF EXISTS follows;
CREATE TABLE follows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    follower_id INT NOT NULL,
    followed_type ENUM('journey', 'user', 'location') NOT NULL,
    followed_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Records all edit actions performed on journeys by staff
DROP TABLE IF EXISTS edit_history;
CREATE TABLE edit_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    journey_id INT,
    event_id INT,
    editor_id INT NOT NULL,
    edit_type ENUM('text', 'image', 'location') NOT NULL,
    edit_reason TEXT NOT NULL,
    edit_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (journey_id) REFERENCES journeys(id) ON DELETE CASCADE,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (editor_id) REFERENCES users(id) ON DELETE CASCADE,
    CHECK (
        (journey_id IS NOT NULL AND event_id IS NULL) OR
        (journey_id IS NULL AND event_id IS NOT NULL)
    )
);

-- Stores user appeals for hidden journeys, bans, or sharing blocks
DROP TABLE IF EXISTS appeals;
CREATE TABLE appeals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    journey_id INT,
    appeal_type ENUM('hidden_journey', 'block_sharing', 'site_ban') NOT NULL,
    content TEXT NOT NULL,
    status ENUM('pending', 'reviewed', 'resolved') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores helpdesk requests submitted by users
DROP TABLE IF EXISTS help_requests;
CREATE TABLE help_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    category ENUM('technical', 'account', 'content', 'bug', 'other') NOT NULL,
    status ENUM('new', 'in_progress', 'on_hold', 'resolved') DEFAULT 'new',
    assigned_to INT,
    assigned_at TIMESTAMP NULL,
    abandoned_at TIMESTAMP NULL,
    hold_reason TEXT,
    resolution_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- Stores attachments for help requests
DROP TABLE IF EXISTS help_request_attachments;
CREATE TABLE help_request_attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE
);

-- Stores bug report specific data
DROP TABLE IF EXISTS help_request_bug_data;
CREATE TABLE help_request_bug_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    steps TEXT,
    expected_behavior TEXT,
    actual_behavior TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE
);

-- Stores replies to helpdesk requests
DROP TABLE IF EXISTS help_request_replies;
CREATE TABLE help_request_replies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores user custom themes and premade theme options
DROP TABLE IF EXISTS themes;
CREATE TABLE themes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    is_premade BOOLEAN DEFAULT FALSE,
    colors JSON,
    background_image VARCHAR(255),
    layout_settings JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Stores latitude and longitude for each location
DROP TABLE IF EXISTS location_coordinates;
CREATE TABLE location_coordinates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    location_id INT NOT NULL,
    latitude DECIMAL(10,8) NOT NULL,
    longitude DECIMAL(11,8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
);

-- Stores destination locations for events (e.g. for flights)
DROP TABLE IF EXISTS event_destinations;
CREATE TABLE event_destinations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    location_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
    FOREIGN KEY (location_id) REFERENCES locations(id) ON DELETE CASCADE
);

-- 支付历史记录表
DROP TABLE IF EXISTS payment_history;
CREATE TABLE payment_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    subscription_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    gst_amount DECIMAL(10,2) DEFAULT 0,
    payment_method VARCHAR(50) NOT NULL,
    payment_date DATETIME NOT NULL,
    receipt_url VARCHAR(255),
    is_free_trial BOOLEAN DEFAULT FALSE,
    billing_country VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (subscription_id) REFERENCES user_subscriptions(id) ON DELETE CASCADE
);

-- Insert subscription plans
INSERT INTO subscription_plans (name, months, discount, price_nz, price_other)
VALUES
  ('Free Trial', 1, 0, 0.00, 0.00),
  ('One Month', 1, 0, 6.00, 5.22),
  ('One Quarter', 3, 10, 16.20, 14.09),
  ('One Year', 12, 25, 54.00, 46.96);