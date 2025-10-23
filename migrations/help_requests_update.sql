-- add category into help_requests
ALTER TABLE help_requests
ADD COLUMN category ENUM('technical', 'account', 'content', 'bug', 'other') NOT NULL DEFAULT 'other' AFTER content;

-- create help_request_attachments
CREATE TABLE IF NOT EXISTS help_request_attachments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE
);

-- create help_request_bug_data
CREATE TABLE IF NOT EXISTS help_request_bug_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    steps TEXT,
    expected_behavior TEXT,
    actual_behavior TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES help_requests(id) ON DELETE CASCADE
); 