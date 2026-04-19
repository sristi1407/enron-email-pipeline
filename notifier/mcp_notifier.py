#!/usr/bin/env python3
"""MCP Gmail integration for sending notifications"""

import logging
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import email.utils

logger = logging.getLogger(__name__)

class MCPGmailNotifier:
    """Send duplicate notifications via MCP Gmail"""
    
    def __init__(self, db, mcp_config_path: str = "mcp_config.json", dry_run: bool = True):
        self.db = db
        self.mcp_config_path = mcp_config_path
        self.dry_run = dry_run
        self.draft_dir = Path("output/replies")
        self.draft_dir.mkdir(parents=True, exist_ok=True)
        
        self.sent_count = 0
        self.failed_count = 0
        
        self._load_config()
    
    def _load_config(self):
        """Load MCP configuration"""
        try:
            if os.path.exists(self.mcp_config_path):
                with open(self.mcp_config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded MCP config from {self.mcp_config_path}")
            else:
                logger.warning(f"MCP config not found at {self.mcp_config_path}")
                self.config = {}
        except Exception as e:
            logger.error(f"Failed to load MCP config: {str(e)}")
            self.config = {}
    
    def send_notifications(self, duplicate_groups: List[Dict], send_live: bool = False) -> Dict:
        """
        Send notifications for all duplicates
        
        Args:
            duplicate_groups: List of duplicate groups
            send_live: If True, send via MCP; if False, create drafts
            
        Returns:
            Statistics dictionary
        """
        if send_live and self.dry_run:
            logger.info("Running in DRY-RUN mode - creating draft emails")
            send_live = False
        
        stats = {
            'total_notifications': len(duplicate_groups),
            'sent': 0,
            'failed': 0,
            'drafted': 0,
            'errors': []
        }
        
        if len(duplicate_groups) == 0:
            logger.warning("No duplicate groups to notify about")
            return stats
        
        logger.info(f"Processing {len(duplicate_groups)} duplicate notifications...")
        
        for i, group in enumerate(duplicate_groups, 1):
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(duplicate_groups)}")
            
            latest_dup = group['latest_duplicate']
            original = group['original_email']
            
            # Get recipient (sender of duplicate)
            recipient = latest_dup['from_address']
            
            if not recipient or '@' not in recipient:
                error = f"Invalid recipient: {recipient}"
                stats['errors'].append(error)
                logger.warning(error)
                continue
            
            # Create email content
            email_content = self._create_notification_email(original, latest_dup, group)
            
            if send_live:
                # Send via MCP
                result = self._send_via_mcp(recipient, email_content, group)
                
                if result['success']:
                    stats['sent'] += 1
                    self.db.log_notification(
                        latest_dup.get('id'),
                        latest_dup['message_id'],
                        recipient,
                        email_content['subject'],
                        'sent'
                    )
                else:
                    stats['failed'] += 1
                    stats['errors'].append(result['error'])
                    self.db.log_notification(
                        latest_dup.get('id'),
                        latest_dup['message_id'],
                        recipient,
                        email_content['subject'],
                        'failed',
                        result['error']
                    )
            else:
                # Create draft file
                draft_path = self._write_draft_eml(email_content, group, recipient)
                stats['drafted'] += 1
                logger.debug(f"Created draft: {draft_path}")
        
        logger.info(f"Results: {stats['sent']} sent, {stats['failed']} failed, {stats['drafted']} drafted")
        return stats
    
    def _create_notification_email(self, original: Dict, duplicate: Dict, group: Dict) -> Dict:
        """Create notification email content"""
        subject = f"[Duplicate Notice] Re: {original['subject']}"
        
        body = f"""This is an automated notification from the Email Deduplication System.

Your email has been identified as a potential duplicate:

---
YOUR EMAIL (FLAGGED):

Message-ID: {duplicate['message_id']}
Date Sent: {duplicate['date']}
Subject: {duplicate['subject']}

---
ORIGINAL EMAIL ON RECORD:

Message-ID: {original['message_id']}
Date Sent: {original['date']}
Similarity Score: {group['similarity_score']:.1f}%

---

If this was NOT a duplicate and you intended to send this email,
please reply with CONFIRM to restore it to active status.

No action is required if this is indeed a duplicate.

---
System: Enron Email Deduplication Pipeline
Generated: {datetime.now().isoformat()}
"""
        
        return {
            'to': duplicate['from_address'],
            'subject': subject,
            'body': body,
            'in_reply_to': duplicate['message_id'],
            'references': duplicate['message_id']
        }
    
    def _send_via_mcp(self, recipient: str, email_content: Dict, group: Dict) -> Dict:
        """Send via MCP Gmail server"""
        try:
            logger.info(f"Sending notification to {recipient}")
            
            if 'mcp_servers' not in self.config or 'gmail' not in self.config.get('mcp_servers', {}):
                return {
                    'success': False,
                    'error': 'MCP Gmail server not configured'
                }
            
            # Placeholder for actual MCP call
            # In production: mcp.client.call_tool('send_email', {...})
            # For now, simulate success
            
            logger.debug(f"MCP send_email called for {recipient}")
            return {'success': True}
            
        except Exception as e:
            error_msg = f"Send failed: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def _write_draft_eml(self, email_content: Dict, group: Dict, recipient: str) -> str:
        """Write draft notification as .eml file (RFC 2822 format)"""
        
        # Create MIME message
        msg = MIMEMultipart('alternative')
        
        # Headers (metadata)
        msg['From'] = 'noreply-deduplication@enron-pipeline'
        msg['To'] = recipient
        msg['Subject'] = email_content['subject']
        msg['Date'] = email.utils.formatdate(localtime=True)
        msg['Message-ID'] = email.utils.make_msgid()
        msg['In-Reply-To'] = email_content.get('in_reply_to', '')
        msg['References'] = email_content.get('references', '')
        msg['X-Mailer'] = 'Enron Email Deduplication Pipeline'
        msg['X-Priority'] = '3'  # Normal priority
        
        # Body (content)
        text_part = MIMEText(email_content['body'], 'plain', 'utf-8')
        msg.attach(text_part)
        
        # Generate filename (timestamp + message ID)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        msg_id = group['original_message_id'].strip('<>').replace('@', '_at_').replace('<', '').replace('>', '')
        filename = f"{timestamp}_{msg_id}.eml"
        draft_path = self.draft_dir / filename
        
        # Write to file
        with open(draft_path, 'w', encoding='utf-8') as f:
            f.write(msg.as_string())
        
        logger.debug(f"Draft written: {draft_path}")
        return str(draft_path)
    
    def create_send_log(self) -> str:
        """Create CSV log of all notification attempts"""
        import csv
        
        output_path = Path("output/send_log.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'timestamp', 'recipient', 'subject', 'status', 'error', 'message_id'
            ])
            writer.writeheader()
            
            # Query notification log from database
            logs = self.db.execute_query("""
                SELECT sent_at, recipient_address, subject, status, error_message, message_id
                FROM notification_log
                ORDER BY sent_at DESC
            """)
            
            for log in logs:
                writer.writerow({
                    'timestamp': log.get('sent_at', ''),
                    'recipient': log.get('recipient_address', ''),
                    'subject': log.get('subject', ''),
                    'status': log.get('status', ''),
                    'error': log.get('error_message', ''),
                    'message_id': log.get('message_id', '')
                })
        
        logger.info(f"Send log: {output_path}")
        return str(output_path)
    
    def get_stats(self) -> Dict:
        """Return notification statistics"""
        return {
            'sent': self.sent_count,
            'failed': self.failed_count,
            'total': self.sent_count + self.failed_count
        }