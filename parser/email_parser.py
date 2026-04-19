 #!/usr/bin/env python3
"""RFC 2822 email parser with field extraction"""

import logging
import hashlib
from pathlib import Path
from email.parser import BytesParser
from email import policy
from typing import Optional, Dict

from utils.date_utils import parse_email_date
from utils.text_utils import (
    extract_email_address,
    extract_email_list,
    extract_headings,
    separate_body_content
)

logger = logging.getLogger(__name__)

class EmailParser:
    """Parse raw RFC 2822 email files and extract structured fields"""
    
    def __init__(self):
        self.parse_errors = []
        self.stats = {
            'total_files': 0,
            'successfully_parsed': 0,
            'failed_parse': 0,
            'field_completeness': {}
        }
    
    def parse_file(self, file_path: Path) -> Optional[Dict]:
        """
        Parse single email file
        
        Args:
            file_path: Path to raw email file
            
        Returns:
            Dictionary with extracted fields or None if failed
        """
        try:
            self.stats['total_files'] += 1
            
            # Read as binary (handles encoding)
            with open(file_path, 'rb') as f:
                raw_email = f.read()
            
            # Parse using RFC 2822 compliant parser
            parser = BytesParser(policy=policy.default)
            msg = parser.parsebytes(raw_email)
            
            # Extract MANDATORY fields
            email_data = {
                'source_file': str(file_path),
            }
            
            # Message ID
            message_id = msg.get('Message-ID', '').strip()
            if not message_id:
                message_id = self._generate_message_id(file_path)
            email_data['message_id'] = message_id
            
            # Date
            email_data['date'] = parse_email_date(msg.get('Date', ''))
            
            # From address
            email_data['from_address'] = extract_email_address(msg.get('From', ''))
            
            # To addresses
            email_data['to_addresses'] = extract_email_list(msg.get('To', ''))
            
            # Subject
            email_data['subject'] = msg.get('Subject', '').strip()
            
            # Body (separated into main/forwarded/quoted)
            raw_body = self._extract_raw_body(msg)
            body, forwarded, quoted = separate_body_content(raw_body)
            email_data['body'] = body
            email_data['forwarded_content'] = forwarded
            email_data['quoted_content'] = quoted
            
            # Extract OPTIONAL fields
            email_data['cc_addresses'] = extract_email_list(msg.get('Cc', ''))
            email_data['bcc_addresses'] = extract_email_list(msg.get('Bcc', ''))
            
            # Enron-specific headers
            email_data['x_from'] = msg.get('X-From', '').strip() or None
            email_data['x_to'] = msg.get('X-To', '').strip() or None
            email_data['x_cc'] = msg.get('X-cc', '').strip() or None
            email_data['x_bcc'] = msg.get('X-bcc', '').strip() or None
            email_data['x_folder'] = msg.get('X-Folder', '').strip() or None
            email_data['x_origin'] = msg.get('X-Origin', '').strip() or None
            
            # Content type and attachments
            email_data['content_type'] = msg.get('Content-Type', '').strip() or None
            email_data['has_attachment'] = self._detect_attachments(msg)
            
            # Headings
            email_data['headings'] = extract_headings(body)
            
            self.stats['successfully_parsed'] += 1
            self._update_field_completeness(email_data)
            
            logger.debug(f"Successfully parsed: {file_path}")
            return email_data
            
        except Exception as e:
            self.stats['failed_parse'] += 1
            error_msg = f"{file_path}: {str(e)}"
            self.parse_errors.append(error_msg)
            logger.error(f"Parse failed: {error_msg}")
            return None
    
    def parse_directory(self, maildir_path: Path, pattern: str = "*") -> list:
        """
        Recursively parse all email files in directory
        
        Args:
            maildir_path: Path to maildir structure
            pattern: File glob pattern (default: all files)
            
        Returns:
            List of parsed email dictionaries
        """
        if not maildir_path.exists():
            logger.warning(f"Maildir path not found: {maildir_path}")
            return []
        
        email_files = [
            f for f in maildir_path.rglob(pattern)
            if f.is_file() and not f.name.startswith('.')
        ]
        
        logger.info(f"Found {len(email_files)} files to parse")
        
        emails = []
        for i, email_file in enumerate(email_files, 1):
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(email_files)} files")
            
            email_data = self.parse_file(email_file)
            if email_data:
                emails.append(email_data)
        
        return emails
    
    def _extract_raw_body(self, msg) -> str:
        """Extract body from multipart or plain text"""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            return payload.decode('utf-8', errors='ignore')
                        else:
                            return payload
            else:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    return payload.decode('utf-8', errors='ignore')
                else:
                    return payload
        except Exception as e:
            logger.warning(f"Error extracting body: {str(e)}")
        
        return ""
    
    def _detect_attachments(self, msg) -> bool:
        """Check if message has attachments"""
        try:
            if msg.is_multipart():
                for part in msg.iter_attachments():
                    return True
        except:
            pass
        return False
    
    def _generate_message_id(self, file_path: Path) -> str:
        """Generate message ID if missing"""
        from datetime import datetime
        hash_input = f"{file_path}{datetime.now().isoformat()}".encode()
        hash_hex = hashlib.md5(hash_input).hexdigest()
        return f"<generated_{hash_hex}@enron-pipeline>"
    
    def _update_field_completeness(self, email_data: Dict):
        """Track field completeness for statistics"""
        mandatory_fields = ['message_id', 'date', 'from_address', 'to_addresses', 'subject', 'body']
        
        for field in mandatory_fields:
            if field not in self.stats['field_completeness']:
                self.stats['field_completeness'][field] = {'present': 0, 'missing': 0}
            
            if email_data.get(field):
                self.stats['field_completeness'][field]['present'] += 1
            else:
                self.stats['field_completeness'][field]['missing'] += 1
    
    def get_stats(self) -> Dict:
        """Return parsing statistics"""
        return self.stats.copy()