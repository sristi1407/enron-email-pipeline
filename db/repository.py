#!/usr/bin/env python3
"""SQLite database repository with connection management"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class EmailRepository:
    """Repository pattern for email database operations"""
    
    def __init__(self, db_path: str = "emails.db"):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / 'schema.sql'
        
        if not schema_path.exists():
            logger.warning(f"Schema file not found: {schema_path}")
            return
        
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        with self._get_connection() as conn:
            conn.executescript(schema)
            logger.info("Database schema initialized")
    
    # ==================== EMAIL OPERATIONS ====================
    
    def insert_email(self, email_data: Dict) -> Optional[int]:
        """Insert email with normalized recipients"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Insert main email
                cursor.execute("""
                    INSERT INTO emails (
                        message_id, date, from_address, subject, body,
                        source_file, x_from, x_folder, x_origin, content_type,
                        has_attachment, forwarded_content, quoted_content, headings
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    email_data.get('message_id'),
                    email_data.get('date'),
                    email_data.get('from_address', ''),
                    email_data.get('subject', ''),
                    email_data.get('body'),
                    email_data.get('source_file'),
                    email_data.get('x_from'),
                    email_data.get('x_folder'),
                    email_data.get('x_origin'),
                    email_data.get('content_type'),
                    1 if email_data.get('has_attachment') else 0,
                    email_data.get('forwarded_content'),
                    email_data.get('quoted_content'),
                    email_data.get('headings')
                ))
                
                email_id = cursor.lastrowid
                
                # Insert TO recipients
                for recipient in email_data.get('to_addresses', []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO email_recipients_to (email_id, recipient_address)
                        VALUES (?, ?)
                    """, (email_id, recipient))
                
                # Insert CC recipients
                for recipient in email_data.get('cc_addresses', []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO email_recipients_cc (email_id, recipient_address)
                        VALUES (?, ?)
                    """, (email_id, recipient))
                
                # Insert BCC recipients
                for recipient in email_data.get('bcc_addresses', []):
                    cursor.execute("""
                        INSERT OR IGNORE INTO email_recipients_bcc (email_id, recipient_address)
                        VALUES (?, ?)
                    """, (email_id, recipient))
                
                # Insert X-headers
                if any([email_data.get('x_to'), email_data.get('x_cc'), email_data.get('x_bcc')]):
                    cursor.execute("""
                        INSERT INTO email_x_headers (email_id, x_to, x_cc, x_bcc)
                        VALUES (?, ?, ?, ?)
                    """, (email_id, email_data.get('x_to'), email_data.get('x_cc'), email_data.get('x_bcc')))
                
                logger.debug(f"Inserted email: {email_data.get('message_id')}")
                return email_id
                
        except sqlite3.IntegrityError:
            logger.debug(f"Email already exists: {email_data.get('message_id')}")
            return None
        except Exception as e:
            logger.error(f"Error inserting email: {str(e)}")
            return None
    
    def get_email_by_message_id(self, message_id: str) -> Optional[Dict]:
        """Retrieve email by message ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails WHERE message_id = ?", (message_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_emails(self, limit: Optional[int] = None) -> List[Dict]:
        """Get all emails"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM emails ORDER BY date ASC"
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_non_duplicate_emails(self) -> List[Dict]:
        """Get emails not marked as duplicates"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM emails WHERE is_duplicate = 0 ORDER BY date ASC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_email_count(self) -> int:
        """Get total email count"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM emails")
            return cursor.fetchone()[0]
    
    def get_duplicate_count(self) -> int:
        """Get count of duplicate emails"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM emails WHERE is_duplicate = 1")
            return cursor.fetchone()[0]
    
    # ==================== DUPLICATE OPERATIONS ====================
    
    def mark_as_duplicate(self, duplicate_message_id: str, original_message_id: str, similarity_score: float):
        """Mark email as duplicate"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE emails
                SET is_duplicate = 1, duplicate_of = ?, similarity_score = ?
                WHERE message_id = ?
            """, (original_message_id, similarity_score, duplicate_message_id))
            logger.debug(f"Marked {duplicate_message_id} as duplicate of {original_message_id}")
    
    def insert_duplicate_group(self, original_message_id: str, latest_duplicate_message_id: str,
                              group_size: int, similarity_score: float = None):
        """Insert duplicate group record"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO duplicate_groups 
                (original_message_id, latest_duplicate_message_id, group_size, similarity_score)
                VALUES (?, ?, ?, ?)
            """, (original_message_id, latest_duplicate_message_id, group_size, similarity_score))
    
    def get_duplicate_groups(self) -> List[Dict]:
        """Get all duplicate groups"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM duplicate_groups ORDER BY group_size DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== LOGGING OPERATIONS ====================
    
    def log_parse_error(self, source_file: str, error_reason: str):
        """Log parse error"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO parse_errors (source_file, error_reason)
                VALUES (?, ?)
            """, (source_file, error_reason))
    
    def log_notification(self, email_id: int, message_id: str, recipient: str,
                        subject: str, status: str, error_msg: str = None):
        """Log notification send attempt"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO notification_log
                (email_id, message_id, recipient_address, subject, sent_at, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (email_id, message_id, recipient, subject, datetime.now(), status, error_msg))
    
    def mark_notification_sent(self, email_id: int):
        """Mark notification as sent"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE emails
                SET notification_sent = 1, notification_date = ?
                WHERE id = ?
            """, (datetime.now(), email_id))
    
    def insert_stats(self, stats: Dict):
        """Insert processing statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO processing_stats
                (total_files_found, successfully_parsed, failed_parse, total_emails_in_db,
                 duplicate_groups_found, emails_flagged_duplicate, avg_group_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                stats.get('total_files', 0),
                stats.get('successfully_parsed', 0),
                stats.get('failed_parse', 0),
                stats.get('total_emails_in_db', 0),
                stats.get('duplicate_groups_found', 0),
                stats.get('emails_flagged_duplicate', 0),
                stats.get('avg_group_size', 0)
            ))
    
    # ==================== QUERY OPERATIONS ====================
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute custom SQL query"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]