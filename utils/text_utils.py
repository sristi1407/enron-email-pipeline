#!/usr/bin/env python3
"""Text processing utilities"""

import re
import logging

logger = logging.getLogger(__name__)

def extract_email_address(email_str: str) -> str:
    """Extract email from 'Name <email@domain>' format"""
    if not email_str:
        return ""
    
    # Try to match standard email pattern
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', email_str)
    
    if match:
        return match.group(0).lower()
    
    return email_str.strip().lower()

def extract_email_list(recipients_str: str) -> list:
    """Parse comma-separated email list and normalize"""
    if not recipients_str:
        return []
    
    # Collapse whitespace
    recipients_str = re.sub(r'\s+', ' ', recipients_str)
    
    addresses = []
    for addr in recipients_str.split(','):
        email_addr = extract_email_address(addr.strip())
        if email_addr and '@' in email_addr:
            addresses.append(email_addr)
    
    return list(set(addresses))  # Remove duplicates

def normalize_subject(subject: str) -> str:
    """Normalize subject by removing Re:/Fwd: prefixes"""
    if not subject:
        return ""
    
    # Remove Re:, Fwd:, RE:, FW: prefixes (case-insensitive)
    normalized = re.sub(
        r'^(re:|fwd:|fw:|re\[.*?\]:|fwd\[.*?\]:)\s*',
        '',
        subject,
        flags=re.IGNORECASE
    )
    
    # Remove bracketed additions
    normalized = re.sub(r'\[.*?\]', '', normalized)
    
    return normalized.strip().lower()

def extract_headings(body: str) -> str:
    """Extract markdown-style headings from text"""
    if not body:
        return None
    
    headings = [
        line.strip() 
        for line in body.split('\n') 
        if line.strip().startswith('#')
    ]
    
    return '\n'.join(headings) if headings else None

def separate_body_content(body_text: str) -> tuple:
    """Separate body into main/forwarded/quoted content"""
    if not body_text:
        return None, None, None
    
    lines = body_text.split('\n')
    body_lines = []
    quoted_lines = []
    forwarded_text = ""
    in_forwarded = False
    
    for line in lines:
        if line.strip().startswith('---') and 'Forwarded by' in line:
            in_forwarded = True
        elif line.strip().startswith('>'):
            quoted_lines.append(line)
        elif in_forwarded:
            forwarded_text += line + '\n'
        else:
            body_lines.append(line)
    
    body = '\n'.join(body_lines).strip() or None
    quoted = '\n'.join(quoted_lines).strip() or None
    forwarded = forwarded_text.strip() or None
    
    return body, forwarded, quoted

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."