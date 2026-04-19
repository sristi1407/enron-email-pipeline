-- Enron Email Pipeline Database Schema (SQLite)
-- Complete normalized schema with indexes

-- Main emails table
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT UNIQUE NOT NULL,
    date DATETIME NOT NULL,
    from_address TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT,
    source_file TEXT NOT NULL,
    x_from TEXT,
    x_folder TEXT,
    x_origin TEXT,
    content_type TEXT,
    has_attachment BOOLEAN DEFAULT 0,
    forwarded_content TEXT,
    quoted_content TEXT,
    headings TEXT,
    is_duplicate BOOLEAN DEFAULT 0,
    duplicate_of TEXT,
    similarity_score REAL,
    notification_sent BOOLEAN DEFAULT 0,
    notification_date DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- TO recipients (normalized)
CREATE TABLE IF NOT EXISTS email_recipients_to (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    recipient_address TEXT NOT NULL,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    UNIQUE(email_id, recipient_address)
);

-- CC recipients (normalized)
CREATE TABLE IF NOT EXISTS email_recipients_cc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    recipient_address TEXT NOT NULL,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    UNIQUE(email_id, recipient_address)
);

-- BCC recipients (normalized)
CREATE TABLE IF NOT EXISTS email_recipients_bcc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL,
    recipient_address TEXT NOT NULL,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    UNIQUE(email_id, recipient_address)
);

-- Enron-specific X-headers
CREATE TABLE IF NOT EXISTS email_x_headers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER NOT NULL UNIQUE,
    x_to TEXT,
    x_cc TEXT,
    x_bcc TEXT,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE
);

-- Duplicate group tracking
CREATE TABLE IF NOT EXISTS duplicate_groups (
    group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_message_id TEXT NOT NULL,
    latest_duplicate_message_id TEXT NOT NULL,
    group_size INTEGER NOT NULL,
    similarity_score REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Processing statistics
CREATE TABLE IF NOT EXISTS processing_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_files_found INTEGER,
    successfully_parsed INTEGER,
    failed_parse INTEGER,
    total_emails_in_db INTEGER,
    duplicate_groups_found INTEGER,
    emails_flagged_duplicate INTEGER,
    avg_group_size REAL
);

-- Notification audit log
CREATE TABLE IF NOT EXISTS notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER,
    message_id TEXT,
    recipient_address TEXT,
    subject TEXT,
    sent_at DATETIME,
    status TEXT,
    error_message TEXT,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE SET NULL
);

-- Parse error log
CREATE TABLE IF NOT EXISTS parse_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    error_reason TEXT NOT NULL,
    error_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_emails_date ON emails(date);
CREATE INDEX IF NOT EXISTS idx_emails_from_address ON emails(from_address);
CREATE INDEX IF NOT EXISTS idx_emails_subject ON emails(subject);
CREATE INDEX IF NOT EXISTS idx_emails_is_duplicate ON emails(is_duplicate);
CREATE INDEX IF NOT EXISTS idx_emails_message_id ON emails(message_id);
CREATE INDEX IF NOT EXISTS idx_recipient_to_address ON email_recipients_to(recipient_address);
CREATE INDEX IF NOT EXISTS idx_recipient_cc_address ON email_recipients_cc(recipient_address);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_original ON duplicate_groups(original_message_id);
CREATE INDEX IF NOT EXISTS idx_notification_log_message_id ON notification_log(message_id);