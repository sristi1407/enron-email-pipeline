# Enron Email Dataset - AI-Assisted Pipeline with MCP Integration

A complete end-to-end pipeline for extracting, structuring, deduplicating, and managing the Enron Email Dataset using Python and SQLite, with MCP Gmail integration for automated notifications.

## Overview

This project implements a full data engineering pipeline that:

1. **Extracts** emails from raw RFC 2822 format files
2. **Parses** and normalizes email data with robust error handling
3. **Stores** emails in SQLite with proper schema normalization
4. **Detects** duplicates using fuzzy matching (90% similarity threshold)
5. **Flags** duplicate emails and creates tracking records
6. **Sends** automated notifications via MCP Gmail server integration
7. **Generates** comprehensive reports and audit logs

## Architecture

```
maildir/
  └── <employee_name>/
      └── <folder>/
          └── <raw_email_files>
              ↓
        [EmailParser] → Parse & Extract Fields
              ↓
        [EmailDatabase] → Normalize & Store
              ↓
        [DuplicateDetector] → Fuzzy Match & Flag
              ↓
        [MCPGmailNotifier] → Send Notifications
              ↓
        [Reports] → CSV, Logs, Statistics
```

## Requirements

- **Python**: 3.10 or higher
- **Database**: SQLite 3.x (included with Python)
- **Optional**: PostgreSQL for local installation (requires `psycopg2` in requirements.txt)

## Installation

### 1. Clone or Extract the Project

```bash
cd enron_pipeline
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `python-dateutil`: Flexible date parsing with timezone support
- `fuzzywuzzy`: Fuzzy string matching with Levenshtein distance
- `python-Levenshtein`: C implementation for fast fuzzy matching
- `email-validator`: Email address validation

### 3. Set Up the Database

The database schema is automatically initialized on first run, but you can manually initialize it:

```bash
sqlite3 emails.db < schema.sql
```

This creates tables for:
- `emails` - Main email records
- `email_recipients_*` - Normalized recipient tables (TO, CC, BCC)
- `email_x_headers` - Enron-specific headers
- `duplicate_groups` - Duplicate tracking
- `parse_errors` - Error log
- `notification_log` - Email sending audit trail
- `processing_stats` - Pipeline statistics

### 4. (Optional) Configure MCP Gmail Integration

To enable live email sending via MCP:

1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop Application)
4. Download the credentials JSON file
5. Copy `mcp_config.json.example` to `mcp_config.json`
6. Add your credentials:

```json
{
  "mcp_servers": {
    "gmail": {
      "env": {
        "GMAIL_CLIENT_ID": "your_client_id",
        "GMAIL_CLIENT_SECRET": "your_client_secret",
        "GMAIL_REFRESH_TOKEN": "your_refresh_token"
      }
    }
  }
}
```

## Usage

### Basic Pipeline Run (Dry-Run Mode)

Extract, deduplicate, and create draft notification emails without sending:

```bash
python main.py --maildir maildir --db emails.db
```

This will:
- Parse all emails in the `maildir/` folder
- Store them in `emails.db`
- Detect duplicates using fuzzy matching
- Create draft `.eml` files in `output/replies/`
- Generate reports in `output/`

### Send Live Notifications

Send actual emails via MCP (requires Gmail OAuth configuration):

```bash
python main.py --maildir maildir --db emails.db --send-live
```

### Extraction Only

Process emails without duplicate detection:

```bash
python main.py --extract-only --maildir maildir --db emails.db
```

### Duplicate Detection Only

Skip extraction (assumes emails already in DB) and run duplicate detection:

```bash
python main.py --detect-only --db emails.db
```

## Project Structure

```
enron_pipeline/
├── main.py                      # Pipeline orchestrator
├── email_parser.py              # RFC 2822 email parsing
├── database.py                  # SQLite operations
├── duplicate_detector.py        # Fuzzy matching duplicate detection
├── mcp_notifier.py             # MCP Gmail integration
├── schema.sql                  # Database schema
├── sample_queries.sql          # Example SQL queries (10 samples)
├── requirements.txt            # Python dependencies
├── mcp_config.json.example     # MCP configuration template
├── README.md                   # This file
├── AI_USAGE.md                 # AI tool usage documentation
├── maildir/                    # Email files (to be populated)
├── output/                     # Generated reports
│   ├── duplicates_report.csv
│   ├── error_log.txt
│   ├── extraction_stats.txt
│   ├── send_log.csv
│   └── replies/               # Draft .eml files
└── pipeline.log               # Execution log
```

## Data Extraction Fields

### Mandatory Fields (Required for Every Email)
- **message_id**: Unique message identifier
- **date**: Email send date (normalized to UTC)
- **from_address**: Sender email address
- **to_addresses**: List of TO recipients
- **subject**: Email subject line
- **body**: Email body content
- **source_file**: Original file path for traceability

### Optional Fields (Extracted When Present)
- **cc_addresses**: CC recipients
- **bcc_addresses**: BCC recipients
- **x_from, x_to, x_cc, x_bcc**: Enron-specific display names
- **x_folder**: Mailbox folder (Enron-specific)
- **x_origin**: Email origin (Enron-specific)
- **content_type**: MIME content type
- **has_attachment**: Whether email has attachments
- **forwarded_content**: Extracted forwarded messages
- **quoted_content**: Extracted quoted replies
- **headings**: Markdown-style headings in body

## Duplicate Detection

### Algorithm

Emails are considered duplicates if they share:
1. **Same sender** (`from_address`)
2. **Same normalized subject** (with Re:/Fwd: prefixes removed)
3. **Similar body content** (≥90% fuzzy match similarity)

### Duplicate Identification
- **Original**: Earliest email in the duplicate group
- **Duplicate**: Latest email in the group (primary target for notification)
- All others: Flagged but not notified

### Output
- Database fields: `is_duplicate`, `duplicate_of`, `similarity_score`
- Report file: `duplicates_report.csv` with all duplicate metadata

## Sample Database Queries

10 sample queries are provided in `sample_queries.sql`:

1. **Count emails per sender** - Identify most active senders
2. **Find emails in date range** - Time-based analysis
3. **Find emails with CC recipients** - Recipient analysis
4. **Duplicate detection summary** - View all duplicate groups
5. **Emails with attachments** - Attachment inventory
6. **Processing statistics** - Pipeline run metrics
7. **Most common subjects** - Communication patterns
8. **Notification status** - Track sent notifications
9. **Parse errors summary** - Failure analysis
10. **Email threads** - Sender-recipient communication pairs

Run sample queries:

```bash
sqlite3 emails.db < sample_queries.sql
```

## Notification Emails

When duplicates are detected, the system sends (or drafts) notification emails to the sender of the latest duplicate:

```
To: <sender_of_duplicate>
Subject: [Duplicate Notice] Re: <original_subject>

This is an automated notification from the Email Deduplication System.

Your email has been identified as a potential duplicate:

YOUR EMAIL (FLAGGED):
Message-ID: <...>
Date Sent: <date>
Subject: <subject>

ORIGINAL EMAIL ON RECORD:
Message-ID: <...>
Date Sent: <date>
Similarity Score: 95.3%

If this was NOT a duplicate and you intended to send this email,
please reply with CONFIRM to restore it to active status.

No action is required if this is indeed a duplicate.
```

## Output Files

### Generated in `output/` Directory

- **duplicates_report.csv** - CSV with all detected duplicates and similarity scores
- **error_log.txt** - Parse failures and errors
- **extraction_stats.txt** - Parsing statistics and field completeness
- **send_log.csv** - Notification send attempts and status
- **replies/** - Directory containing draft `.eml` notification files

### Database Tables

- **emails** - All extracted email records
- **email_recipients_*** - Normalized recipient lists
- **duplicate_groups** - Duplicate relationship tracking
- **notification_log** - Email send history
- **parse_errors** - Failed parse attempts
- **processing_stats** - Pipeline metrics

## Enron Dataset

The pipeline is designed for the Enron Email Dataset:

**Download:** https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz (approximately 500MB)

**Recommended mailboxes** for testing:
- `lay-k` - Ken Lay (CEO)
- `skilling-j` - Jeff Skilling (President)
- `enron_general` - General mailing list
- `jones-t` - Tom Jones
- `davis-d` - Don Davis

Extract and place in `maildir/` folder:

```bash
tar xzf enron_mail_20150507.tar.gz
mv maildir/* enron_pipeline/maildir/
```

## Error Handling

The pipeline gracefully handles:
- Malformed email files
- Missing headers
- Invalid email addresses
- Encoding issues (UTF-8, Latin-1, etc.)
- Timezone parsing failures
- Duplicate message IDs
- Multipart MIME messages
- Forwarded and quoted content

All failures are logged to `error_log.txt` with file paths and specific error reasons.

## Performance Considerations

- **Parsing**: Processes ~50-100 emails/second depending on file size
- **Duplicate Detection**: O(n²) in worst case; optimized with sender/subject grouping
- **Database**: Indexed on date, from_address, subject for fast queries
- **Memory**: Loads emails into memory for duplicate comparison; suitable for datasets up to 500K emails

For very large datasets (>1M emails), consider:
- Batch processing by sender
- Incremental duplicate detection
- Database connection pooling

## Logging

Pipeline logs to both file and console:

- **File**: `pipeline.log` - Complete execution log
- **Console**: Real-time progress updates
- **Database**: Error, notification, and statistics tables

Log levels:
- `DEBUG`: Detailed processing steps
- `INFO`: Major milestones and counts
- `WARNING`: Issues that don't stop execution
- `ERROR`: Failed operations

## Troubleshooting

### Issue: "No module named email_parser"
**Solution:** Ensure all `.py` files are in the same directory as `main.py`

### Issue: Database locked
**Solution:** Close any other connections to `emails.db` and retry

### Issue: MCP Gmail not configured
**Solution:** Create `mcp_config.json` with valid Gmail OAuth credentials, or run in dry-run mode (default)

### Issue: High parse failure rate
**Solution:** Check error_log.txt; may indicate encoding issues or invalid email format

### Issue: Duplicate detection is slow
**Solution:** Reduce dataset size for testing, or implement batch processing for full dataset

## MCP Integration Details

### MCP Server Communication

The `mcp_notifier.py` module implements MCP (Model Context Protocol) integration:

```python
# Example MCP call structure
await mcp.call_tool(
    'send_email',
    {
        'to': 'recipient@example.com',
        'subject': '[Duplicate Notice] Re: Subject',
        'body': 'Notification body...',
        'in_reply_to': '<original_message_id>',
        'references': '<message_id>'
    }
)
```

### Dry-Run Mode

By default, the system creates `.eml` files instead of sending:
- Located in `output/replies/`
- Can be manually imported into email clients
- Shows exactly what would be sent

### Live Mode

With `--send-live` flag:
- Requires valid MCP Gmail server configuration
- Sends actual emails
- Logs all attempts in `notification_log` database table
- Updates `notification_sent` field when successful

## AI Tool Usage

See `AI_USAGE.md` for detailed documentation on:
- How Claude Code was used to develop this system
- Prompting strategies and iterations
- Code generation vs. manual implementation
- Debugging and refinement process
- MCP integration approach

## License

This project is provided for educational and evaluation purposes.

## Support

For issues or questions, refer to:
1. `AI_USAGE.md` - AI development process documentation
2. `pipeline.log` - Execution logs with detailed error messages
3. `output/error_log.txt` - Parse failure details
4. Database tables - `parse_errors`, `notification_log` for audit trail