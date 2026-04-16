# Kiwi Travel Behaviour Analytics Application

## Project Overview

This project is a Kiwi travel behaviour analytics application that captures and structures user journey data, enabling analysis of Kiwi travel patterns, event frequency, and destination trends. The system supports user management, journey and event recording, and subscription-based access to advanced analytics features including published journeys, multi-image event tracking, and journey performance insights.

## Online Demo

Project demo available at: https://teamoam5.pythonanywhere.com

## Local Setup Instructions

### Prerequisites

- Python 3.7+ installed
- MySQL server installed and running
- Git (optional for cloning the repository)

### Create Database and Tables

1. Start your MySQL server
2. Log in to MySQL: `mysql -u your_username -p`
3. Execute the [create_database.sql](create_database.sql) file to create the database and tables:
   ```sql
   mysql -u your_username -p < create_database.sql
   ```
   or copy the contents of the file and paste them into your MySQL console

### Database Configuration

Create a file named `config.py` in the root directory with the following content:

```python
# Database configuration
DB_CONFIG = {
    'user': 'your_mysql_username',
    'password': 'your_mysql_password',
    'host': 'localhost',
    'database': 'travel_journal',
    'port': 3306
}

# Flask secret key (generate a random one for security)
SECRET_KEY = 'your_secret_key_here'
```

### Running on Windows

```bash
# Navigate to project folder
cd "<project folder location>"

# Create virtual environment
python -m venv <virtual_env_name>

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python run.py
```

### Running on Mac/Linux

```bash
# Navigate to project folder
cd "<project folder location>"

# Create virtual environment
python -m venv <virtual_env_name>

# Activate virtual environment
source <virtual_env_name>/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run application
python run.py
```

After running the application, access it by opening http://127.0.0.1:5000 in your web browser.

## User Guide

### Getting Started

1. **Registration**: New users can register by clicking the "Sign Up" button on the home page
2. **Login**: Existing users can log in using their username and password
3. **Navigation**: Use the top navigation bar to access different sections of the application

### Traveler Functions

1. **Creating a Journey**:
   - Click on "Journeys" in the navigation menu
   - Click the "Create a New Journey" button
   - Fill in the journey details (title, description, start dates)
   - Set visibility: Private, Public, or Published (Premium feature)
   - Click "Save" to create the journey

2. **Adding Events to a Journey**:
   - Open a journey from your journey list
   - Click the " + New Event" button
   - Fill in event details (title, description, location, date/time)
   - Upload photos (Premium users can upload multiple images per event)
   - Click "Save" to add the event

3. **Subscription Management**:
   - Access subscription options through your profile
   - Choose from Free Trial (1 month), One Month (NZ$6.00), One Quarter (NZ$16.20), or One Year (NZ$54.00)
   - View subscription status and history
   - Manage premium features based on subscription status

4. **Premium Features**:
   - **Published Journeys**: Make journeys visible to all visitors (including non-logged-in users)
   - **Multiple Images**: Add multiple photos to each event
   - **Journey Cover Images**: Set cover images for journeys
   - **Private Messaging**: Exchange messages with other users
   - **Departure Board**: Follow journeys, users, and locations for personalized feed

5. **Managing Your Profile**:
   - Click on your username in the top-right corner
   - Select "Profile" from the dropdown menu
   - Edit your personal information, change password, or update profile picture

6. **Viewing Other Travelers' Journeys**:
   - Click on "Journeys" in the navigation menu
   - Click Public to view shared journeys
   - Use the search function to find specific journey keywords or locations

### Community Features

1. **Interacting with Content**:
   - Like and comment on shared events
   - Like or dislike comments
   - Report inappropriate content

2. **Following System** (Premium):
   - Follow specific journeys, users, or locations
   - View updates on your Departure Board
   - Manage your following list

### Editor Functions

1. **Content Management**:
   - Edit shared journeys and events
   - Provide reasons for edits (all edits are logged)
   - Hide inappropriate content
   - Handle user appeals

2. **Moderation**:
   - Review reported content
   - Manage community guidelines enforcement

### Administrator Functions

1. **User Management**:
   - Access the "Users" panel
   - View all users, search, and filter by different criteria
   - Edit user information, change roles, or deactivate accounts
   - Grant free subscriptions to users

2. **Subscription Management**:
   - View subscription history for any user
   - Grant complimentary subscription time
   - Monitor payment records and receipts

3. **Content Management**:
   - Manage all content including journeys, events, and comments
   - Remove inappropriate content
   - Handle appeals and disputes

### Support Tech Functions

1. **Helpdesk Management**:
   - Process help requests and bug reports
   - Assign and manage support tickets
   - Prioritize requests from premium subscribers

### Accounts for Testing

| No. | username | password | role         |
|-----|----------|----------|--------------|
| 1   | liam_a   | Q123456q | traveller    |
| 2   | sophia_c | Q123456q | traveller    |
| 3   | mason_p  | Q123456q | traveller    |
| 4   | james_p  | Q123456q | editor       |
| 5   | emily_l  | Q123456q | editor       |
| 6   | will_t   | Q123456q | editor       |
| 7   | ethan_c  | Q123456q | moderator    |
| 8   | olivia_b | Q123456q | moderator    |
| 9   | noah_r   | Q123456q | support_tech |
| 10  | ava_m    | Q123456q | support_tech |
| 11  | lily_b   | Q123456q | admin        |
| 12  | joe_h    | Q123456q | admin        |

## Subscription System

### Subscription Options

- **Free Trial**: 1 month (one-time only per account)
- **One Month**: NZ$6.00 (including GST for NZ billing addresses)
- **One Quarter**: NZ$16.20 (including GST for NZ billing addresses, 10% discount)
- **One Year**: NZ$54.00 (including GST for NZ billing addresses, 25% discount)

### Payment Processing

- Simulated payment gateway for educational purposes
- GST (15%) applied to New Zealand billing addresses only
- Prepaid service model (no auto-renewal)
- Receipt generation for all transactions

### Premium Features

1. **Published Journeys**: Visible to all visitors, including non-logged-in users
2. **Multiple Images**: Upload multiple photos per event
3. **Journey Cover Images**: Set attractive cover images for journeys
4. **Private Messaging**: Communicate with other users
5. **Departure Board**: Personalized feed of followed content
6. **Enhanced User Profiles**: Extended profile customization
7. **Edit History**: View complete edit history for your content
8. **No Edits Flag**: Protect your content from staff edits

## Troubleshooting

1. **Database Connection Issues**:
   - Verify MySQL server is running
   - Check database credentials in `config.py`
   - Ensure the database has been created with correct tables

2. **Application Startup Problems**:
   - Check Python version (3.7+ required)
   - Verify all dependencies are installed
   - Check error logs in the console output

3. **Image Upload Issues**:
   - Verify the `uploads` directory exists and has write permissions
   - Check that the uploaded file type is supported (JPG, PNG, GIF)
   - Ensure file size is below the maximum limit (10MB)

4. **Subscription Issues**:
   - Verify payment gateway simulation is working
   - Check subscription status in user profile
   - Ensure premium features are enabled for active subscribers

## Project Architecture

### Layered Architecture

The project follows a typical layered architecture design:

1. **Presentation Layer**: Flask templates for rendering views, located in `app/templates` directory
2. **Controller Layer**: User interaction handling, in files like `app/user.py`, `app/journey.py`, etc.
3. **Data Access Layer**: Database interaction abstraction, in `app/repository.py` and `app/db.py`
4. **Database Layer**: MySQL database, created through `create_database.sql`

### Module Design

The project is organized into functional modules:

- **User Management Module** (`app/user.py`): Handles user registration, login, profile management
- **Journey Management Module** (`app/journey.py`): Handles journey creation, editing, deletion, viewing
- **Event Management Module** (`app/event.py`): Handles event creation, editing, deletion in journeys
- **Location Management Module** (`app/location.py`): Handles geographic location management
- **Subscription Module** (`app/subscription.py`): Handles subscription management and payments
- **Premium Features Module**: Handles premium functionality and access control
- **Admin Module** (`app/admin.py`): Handles administrator functions, including user management
- **Authentication Module** (`app/auth.py`): Handles user authentication and permission management

## Database Design

The system database includes the following main tables:

1. **locations**: Stores geographic location information
2. **users**: Stores user information, including roles and permissions
3. **journeys**: Stores journey information, associated with users
4. **events**: Stores events in journeys, associated with journeys and locations
5. **photos**: Stores event photos, associated with events
6. **subscriptions**: Stores subscription information and payment history
7. **messages**: Stores private messages between users
8. **follows**: Stores following relationships for users, journeys, and locations
9. **comments**: Stores comments on events
10. **likes**: Stores likes and dislikes on comments
11. **edit_history**: Stores edit history for transparency
12. **support_requests**: Stores helpdesk requests and bug reports

### Security Features

- **Role-Based Access Control**: Different permissions for Travellers, Editors, Admins, Moderators, and Support Techs
- **Subscription Verification**: Premium features are access-controlled based on active subscriptions
- **Edit Logging**: All staff edits are logged with reasons and timestamps
- **Content Moderation**: Comprehensive system for handling inappropriate content
- **Appeals Process**: Users can appeal moderation decisions

## Technology Stack

- **Backend**: Python, Flask
- **Database**: MySQL
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Payment**: Simulated payment gateway
- **Deployment**: PythonAnywhere

## Image Sources

Photos included in the project are taken by **Xinyuan Zhao (Member of OAM team)** in New Zealand using `Sony A7m4` and `GoPro 10` cameras.

## Additional Information

- Project uses MIT license
- Team: OAM Team
- Version: 2.0.0 (Premium Online Travel Journal)
- Course: COMP639 Studio Project - Semester 1 2025
- Project Type: Group Project 2
