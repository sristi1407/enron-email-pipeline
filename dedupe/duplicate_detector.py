#!/usr/bin/env python3
"""Duplicate detection using fuzzy matching"""

import logging
import csv
from pathlib import Path
from typing import List, Dict
from fuzzywuzzy import fuzz

from utils.text_utils import normalize_subject

logger = logging.getLogger(__name__)

MIN_SIMILARITY_THRESHOLD = 90

class DuplicateDetector:
    """Detects duplicate emails using fuzzy matching"""
    
    def __init__(self, db, similarity_threshold: int = MIN_SIMILARITY_THRESHOLD):
        self.db = db
        self.similarity_threshold = similarity_threshold
        self.duplicate_groups = []
        self.stats = {
            'total_groups': 0,
            'total_duplicates': 0,
            'avg_group_size': 0
        }
    
    def detect_all_duplicates(self) -> List[Dict]:
        """
        Scan database and detect all duplicates
        
        Returns:
            List of duplicate groups with metadata
        """
        logger.info("Starting duplicate detection...")
        
        # Get all non-duplicate emails
        emails = self.db.get_non_duplicate_emails()
        
        if not emails:
            logger.info("No emails to process")
            return []
        
        logger.info(f"Analyzing {len(emails)} emails...")
        
        # Step 1: Group by sender + normalized subject
        groups_by_key = {}
        
        for email in emails:
            normalized_subject = normalize_subject(email['subject'])
            key = (email['from_address'], normalized_subject)
            
            if key not in groups_by_key:
                groups_by_key[key] = []
            
            groups_by_key[key].append(email)
        
        logger.info(f"Created {len(groups_by_key)} groups (sender + subject)")
        
        # Step 2: Process each group
        duplicate_groups = []
        processed_count = 0
        
        for (sender, subject), group in groups_by_key.items():
            if len(group) < 2:
                continue  # No duplicates in this group
            
            # Sort by date (earliest first)
            group = sorted(group, key=lambda x: x['date'] if x['date'] else '')
            
            # Find duplicates in group
            duplicates_in_group = self._find_duplicates_in_group(group)
            
            for dup_set in duplicates_in_group:
                group_dict = self._create_duplicate_group(dup_set)
                if group_dict:
                    duplicate_groups.append(group_dict)
                    processed_count += len(dup_set)
        
        # Update statistics
        self.stats['total_groups'] = len(duplicate_groups)
        self.stats['total_duplicates'] = processed_count
        if len(duplicate_groups) > 0:
            self.stats['avg_group_size'] = processed_count / len(duplicate_groups)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups ({processed_count} total emails)")
        
        return duplicate_groups
    
    def _find_duplicates_in_group(self, emails: List[Dict]) -> List[List[Dict]]:
        """Find duplicate subsets within a group"""
        if len(emails) < 2:
            return []
        
        duplicate_sets = []
        checked = set()
        
        # Compare each email with others in the group
        for i, email1 in enumerate(emails):
            if email1['message_id'] in checked:
                continue
            
            group = [email1]
            checked.add(email1['message_id'])
            
            # Check against all later emails
            for j in range(i + 1, len(emails)):
                email2 = emails[j]
                if email2['message_id'] in checked:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_similarity(email1, email2)
                
                # If >= 90% similar, it's a duplicate
                if similarity >= self.similarity_threshold:
                    group.append(email2)
                    checked.add(email2['message_id'])
            
            if len(group) > 1:
                duplicate_sets.append(group)
        
        return duplicate_sets
    
    def _calculate_similarity(self, email1: Dict, email2: Dict) -> float:
        """Calculate similarity score (0-100) using fuzzy matching"""
        body1 = (email1.get('body') or '').strip()
        body2 = (email2.get('body') or '').strip()
        
        # If either body is empty
        if not body1 or not body2:
            return 100.0 if body1 == body2 else 0.0
        
        # Use token_set_ratio for better matching (handles word reordering)
        # This is better than simple ratio for email bodies
        similarity = fuzz.token_set_ratio(body1, body2)
        
        return float(similarity)
    
    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject line by removing reply/forward prefixes"""
        if not subject:
            return ""
        
        # Remove Re:, Fwd:, RE:, FW: prefixes (case-insensitive)
        import re
        normalized = re.sub(r'^(re:|fwd:|fw:|re\[.*?\]:|fwd\[.*?\]:)\s*', '', subject, flags=re.IGNORECASE)
        normalized = re.sub(r'\[.*?\]', '', normalized)  # Remove bracketed additions
        
        return normalized.strip().lower()
    
    def _create_duplicate_group(self, emails: List[Dict]) -> Dict:
        """Create duplicate group record"""
        if len(emails) < 2:
            return None
        
        # Sort by date - earliest is original, latest is duplicate
        sorted_emails = sorted(emails, key=lambda x: x['date'] if x['date'] else '')
        
        original = sorted_emails[0]
        latest_duplicate = sorted_emails[-1]
        
        # Calculate similarity between original and latest
        similarity_score = self._calculate_similarity(original, latest_duplicate)
        
        return {
            'original_email': original,
            'latest_duplicate': latest_duplicate,
            'all_emails': sorted_emails,
            'group_size': len(sorted_emails),
            'similarity_score': similarity_score,
            'original_message_id': original['message_id'],
            'latest_duplicate_message_id': latest_duplicate['message_id'],
            'original_date': original['date'],
            'latest_duplicate_date': latest_duplicate['date'],
            'subject': original['subject'],
            'from_address': original['from_address']
        }
    
    def mark_duplicates_in_db(self, duplicate_groups: List[Dict]):
        """Mark all duplicates in database"""
        total_marked = 0
        
        for group in duplicate_groups:
            # Mark all emails except the earliest as duplicates
            for email in group['all_emails'][1:]:
                self.db.mark_as_duplicate(
                    email['message_id'],
                    group['original_message_id'],
                    group['similarity_score']
                )
                total_marked += 1
            
            # Insert duplicate group record
            self.db.insert_duplicate_group(
                group['original_message_id'],
                group['latest_duplicate_message_id'],
                group['group_size'],
                group['similarity_score']
            )
        
        logger.info(f"Marked {total_marked} emails as duplicates in database")
    
    def generate_report(self, duplicate_groups: List[Dict], output_file: str = "output/duplicates_report.csv") -> str:
        """Generate CSV report of duplicates"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'duplicate_message_id', 'original_message_id', 'subject', 'from_address',
                'duplicate_date', 'original_date', 'similarity_score', 'group_size'
            ])
            writer.writeheader()
            
            for group in duplicate_groups:
                for dup_email in group['all_emails'][1:]:
                    writer.writerow({
                        'duplicate_message_id': dup_email['message_id'],
                        'original_message_id': group['original_message_id'],
                        'subject': group['subject'],
                        'from_address': group['from_address'],
                        'duplicate_date': dup_email['date'],
                        'original_date': group['original_date'],
                        'similarity_score': f"{group['similarity_score']:.2f}",
                        'group_size': group['group_size']
                    })
        
        logger.info(f"Duplicates report: {output_path}")
        return str(output_path)
    
    def get_stats(self) -> Dict:
        """Return statistics"""
        return self.stats.copy()