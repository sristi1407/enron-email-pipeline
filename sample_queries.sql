-- Sample Queries for Enron Email Pipeline Database

-- Query 1: Count emails per sender
-- Expected output: Lists all senders with their email counts, ordered by frequency
SELECT 
    from_address,
    COUNT(*) as email_count,
    MIN(date) as first_email_date,
    MAX(date) as last_email_date
FROM emails
WHERE is_duplicate = 0
GROUP BY from_address
ORDER BY email_count DESC
LIMIT 20;


-- Query 2: Find all emails in a date range
-- Expected output: Emails sent between specific dates, useful for time-based analysis
SELECT 
    message_id,
    date,
    from_address,
    subject,
    is_duplicate
FROM emails
WHERE date >= '2001-01-01' AND date <= '2001-12-31'
ORDER BY date DESC;


-- Query 3: Find emails with CC recipients (includes display of all recipients)
-- Expected output: Shows emails that have CC recipients with normalized recipient lists
SELECT 
    e.message_id,
    e.date,
    e.from_address,
    e.subject,
    GROUP_CONCAT(DISTINCT rt.recipient_address, '; ') as to_recipients,
    GROUP_CONCAT(DISTINCT rc.recipient_address, '; ') as cc_recipients,
    e.is_duplicate
FROM emails e
LEFT JOIN email_recipients_to rt ON e.id = rt.email_id
LEFT JOIN email_recipients_cc rc ON e.id = rc.email_id
WHERE rc.recipient_address IS NOT NULL
GROUP BY e.id
ORDER BY e.date DESC
LIMIT 50;


-- Query 4: Duplicate detection summary
-- Expected output: Shows all duplicate groups with original and duplicate info
SELECT 
    dg.group_id,
    dg.group_size,
    dg.similarity_score,
    e_orig.message_id as original_message_id,
    e_orig.from_address,
    e_orig.subject,
    e_orig.date as original_date,
    e_dup.message_id as latest_duplicate_message_id,
    e_dup.date as duplicate_date
FROM duplicate_groups dg
JOIN emails e_orig ON dg.original_message_id = e_orig.message_id
JOIN emails e_dup ON dg.latest_duplicate_message_id = e_dup.message_id
ORDER BY dg.group_size DESC, e_orig.date DESC;


-- Query 5: Emails with attachments
-- Expected output: Lists all emails that have attachments for further analysis
SELECT 
    message_id,
    date,
    from_address,
    subject,
    has_attachment,
    content_type
FROM emails
WHERE has_attachment = 1
ORDER BY date DESC
LIMIT 50;


-- Query 6: Processing statistics summary
-- Expected output: Overall statistics about the last pipeline run
SELECT 
    run_timestamp,
    total_files_found,
    successfully_parsed,
    failed_parse,
    total_emails_in_db,
    duplicate_groups_found,
    emails_flagged_duplicate,
    ROUND(avg_group_size, 2) as avg_group_size,
    ROUND((successfully_parsed * 100.0 / total_files_found), 2) as parse_success_rate
FROM processing_stats
ORDER BY run_timestamp DESC
LIMIT 1;


-- Query 7: Find most common email subjects
-- Expected output: Top subjects to identify common communication patterns
SELECT 
    SUBSTR(subject, 1, 50) as subject_preview,
    COUNT(*) as email_count,
    COUNT(CASE WHEN is_duplicate = 1 THEN 1 END) as duplicate_count
FROM emails
GROUP BY SUBSTR(subject, 1, 50)
ORDER BY email_count DESC
LIMIT 25;


-- Query 8: Notification status for duplicates
-- Expected output: Shows which duplicates have been notified
SELECT 
    nl.id,
    nl.message_id,
    nl.recipient_address,
    nl.sent_at,
    nl.status,
    e.subject,
    e.date
FROM notification_log nl
LEFT JOIN emails e ON nl.email_id = e.id
ORDER BY nl.sent_at DESC
LIMIT 50;


-- Query 9: Parse errors summary
-- Expected output: Aggregated view of parsing failures by reason
SELECT 
    error_reason,
    COUNT(*) as error_count,
    MIN(error_timestamp) as first_occurrence,
    MAX(error_timestamp) as last_occurrence
FROM parse_errors
GROUP BY error_reason
ORDER BY error_count DESC;


-- Query 10: Email threads (sender-recipient pairs)
-- Expected output: Shows communication patterns between senders and recipients
SELECT 
    e.from_address as sender,
    rt.recipient_address as recipient,
    COUNT(*) as message_count,
    MIN(e.date) as first_email,
    MAX(e.date) as last_email
FROM emails e
JOIN email_recipients_to rt ON e.id = rt.email_id
GROUP BY e.from_address, rt.recipient_address
HAVING message_count > 1
ORDER BY message_count DESC
LIMIT 30;
