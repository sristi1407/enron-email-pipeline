#!/usr/bin/env python3
"""Main pipeline orchestrator - START HERE"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from utils.logger import setup_logger
from parser.email_parser import EmailParser
from db.repository import EmailRepository
from dedupe.duplicate_detector import DuplicateDetector
from notifier.mcp_notifier import MCPGmailNotifier
from reports.report_generator import ReportGenerator

# Setup logging
logger = setup_logger(__name__)

class EnronPipeline:
    """Complete pipeline orchestrator"""
    
    def __init__(self, maildir_path: str = "maildir", db_path: str = "emails.db"):
        self.maildir_path = Path(maildir_path)
        self.db = EmailRepository(db_path)
        self.parser = EmailParser()
        self.detector = DuplicateDetector(self.db)
        self.notifier = MCPGmailNotifier(self.db)
        self.reports = ReportGenerator(self.db)
        
        self.stats = {
            'start_time': None,
            'end_time': None,
            'files_processed': 0,
            'emails_ingested': 0,
            'duplicate_groups': 0,
            'notifications_sent': 0
        }
    
    def run_full_pipeline(self, send_live: bool = False):
        """Execute complete pipeline"""
        self.stats['start_time'] = datetime.now()
        
        print("=" * 70)
        print("ENRON EMAIL PIPELINE - FULL EXECUTION")
        print("=" * 70)
        
        try:
            # Phase 1: Extract
            print("\n[PHASE 1] EMAIL EXTRACTION")
            print("-" * 70)
            self._extract_emails()
            
            # Phase 2: Detect duplicates
            print("\n[PHASE 2] DUPLICATE DETECTION")
            print("-" * 70)
            duplicate_groups = self._detect_duplicates()
            
            # Phase 3: Send notifications
            print("\n[PHASE 3] SEND NOTIFICATIONS")
            print("-" * 70)
            notification_stats = self._send_notifications(duplicate_groups, send_live)
            
            # Phase 4: Generate reports
            print("\n[PHASE 4] GENERATE REPORTS")
            print("-" * 70)
            self._generate_reports(duplicate_groups, notification_stats)
            
            self.stats['end_time'] = datetime.now()
            duration = self.stats['end_time'] - self.stats['start_time']
            
            print("\n" + "=" * 70)
            print("PIPELINE COMPLETE ✅")
            print("=" * 70)
            print(f"Total duration: {duration}")
            print(f"Emails ingested: {self.stats['emails_ingested']}")
            print(f"Duplicate groups: {self.stats['duplicate_groups']}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Pipeline failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
    
    def _extract_emails(self):
        """Extract and ingest emails"""
        if not self.maildir_path.exists():
            print(f"❌ Maildir not found: {self.maildir_path}")
            return
        
        print(f"Scanning maildir: {self.maildir_path}")
        
        # Parse all emails
        emails = self.parser.parse_directory(self.maildir_path)
        print(f"Parsed {len(emails)} emails")
        
        if len(emails) == 0:
            print("⚠️  No emails found to process")
            return
        
        # Ingest to database
        ingested = 0
        for i, email_data in enumerate(emails, 1):
            email_id = self.db.insert_email(email_data)
            if email_id:
                ingested += 1
        
        # Log extraction stats
        parser_stats = self.parser.get_stats()
        self.reports.generate_extraction_stats(parser_stats)
        
        # Log parse errors
        if self.parser.parse_errors:
            self.reports.generate_error_report(self.parser.parse_errors)
        
        self.stats['files_processed'] = parser_stats.get('total_files', 0)
        self.stats['emails_ingested'] = ingested
        
        print(f"✅ Ingested {ingested} emails")
    
    def _detect_duplicates(self):
        """Detect and flag duplicates"""
        email_count = self.db.get_email_count()
        
        if email_count == 0:
            print("⚠️  No emails in database to deduplicate")
            return []
        
        print(f"Running duplicate detection on {email_count} emails...")
        
        # Detect
        duplicate_groups = self.detector.detect_all_duplicates()
        print(f"Found {len(duplicate_groups)} duplicate groups")
        
        if len(duplicate_groups) > 0:
            # Mark in database
            self.detector.mark_duplicates_in_db(duplicate_groups)
            
            # Generate report
            self.detector.generate_report(duplicate_groups)
        
        self.stats['duplicate_groups'] = len(duplicate_groups)
        
        print(f"✅ Detected {len(duplicate_groups)} duplicate groups")
        
        return duplicate_groups
    
    def _send_notifications(self, duplicate_groups, send_live: bool = False):
        """Send notifications"""
        if len(duplicate_groups) == 0:
            print("⚠️  No duplicates to notify about")
            return {'sent': 0, 'drafted': 0, 'total_notifications': 0, 'errors': []}
        
        print(f"Sending notifications (live={send_live})...")
        
        notification_stats = self.notifier.send_notifications(
            duplicate_groups,
            send_live=send_live
        )
        
        # Create send log
        self.notifier.create_send_log()
        
        self.stats['notifications_sent'] = notification_stats.get('sent', 0)
        
        return notification_stats
    
    def _generate_reports(self, duplicate_groups, notification_stats):
        """Generate all reports"""
        print("Generating reports...")
        
        parser_stats = self.parser.get_stats()
        detector_stats = self.detector.get_stats()
        
        # Summary report
        self.reports.generate_summary_report(parser_stats, detector_stats, notification_stats)
        
        # Database summary
        self.reports.generate_database_summary()
        
        print(f"✅ Reports generated in output/")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Enron Email Pipeline - Extract, Deduplicate, Notify'
    )
    parser.add_argument('--maildir', default='maildir',
                       help='Path to maildir (default: maildir)')
    parser.add_argument('--db', default='emails.db',
                       help='Path to database (default: emails.db)')
    parser.add_argument('--send-live', action='store_true',
                       help='Send emails via MCP (default: draft mode)')
    parser.add_argument('--extract-only', action='store_true',
                       help='Only extract emails')
    parser.add_argument('--detect-only', action='store_true',
                       help='Only extract and detect duplicates')
    
    args = parser.parse_args()
    
    try:
        pipeline = EnronPipeline(args.maildir, args.db)
        
        if args.extract_only:
            print("Mode: EXTRACTION ONLY")
            pipeline._extract_emails()
            return 0
        elif args.detect_only:
            print("Mode: EXTRACTION + DETECTION")
            pipeline._extract_emails()
            duplicate_groups = pipeline._detect_duplicates()
            pipeline._generate_reports(duplicate_groups, {'sent': 0, 'drafted': 0, 'total_notifications': 0, 'errors': []})
            return 0
        else:
            print("Mode: FULL PIPELINE")
            return pipeline.run_full_pipeline(send_live=args.send_live)
        
    except Exception as e:
        print(f"❌ Pipeline failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())