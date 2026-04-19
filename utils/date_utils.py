#!/usr/bin/env python3
"""Date parsing utilities with timezone support"""

from datetime import datetime
from email.utils import parsedate_to_datetime
import dateutil.parser as date_parser
import logging

logger = logging.getLogger(__name__)

TIMEZONE_MAP = {
    'PST': '-08:00', 'PDT': '-07:00',
    'MST': '-07:00', 'MDT': '-06:00',
    'CST': '-06:00', 'CDT': '-05:00',
    'EST': '-05:00', 'EDT': '-04:00',
}

def parse_email_date(date_str: str) -> datetime:
    """Parse email date with multiple fallbacks"""
    if not date_str:
        return None
    
    try:
        # Method 1: Standard RFC 2822 parsing
        return parsedate_to_datetime(date_str)
    except (TypeError, ValueError):
        try:
            # Method 2: Fuzzy parsing with dateutil
            return date_parser.parse(date_str, fuzzy=True)
        except:
            logger.warning(f"Could not parse date: {date_str}")
            return None

def normalize_date_to_utc(dt: datetime) -> datetime:
    """Normalize datetime to UTC"""
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        return dt.replace(tzinfo=datetime.timezone.utc)
    
    return dt.astimezone(datetime.timezone.utc)