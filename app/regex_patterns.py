USERNAME_PATTERN = r'^[a-zA-Z0-9_]{3,20}$'  # Username must be 3-20 characters long and contain only letters, numbers, and underscores
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,320}$'  # Email must be less than 320 characters long and be in the format of
PASSWORD_PATTERN = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d\W_]{8,20}$'  # Password must be 8-20 characters long, contain at least one uppercase letter, one lowercase letter, and one number.
NAME_PATTERN = r'^[A-Za-zĀ-Ūā-ū]{2,50}$'  # Name can contain only letters (including Māori macrons), 2 to 50 characters long