#!/usr/bin/env python3
"""Report generation and statistics"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Dict

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Generate reports and statistics"""
    
    def __init__(self, db):
        self.db = db
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_extraction_stats(self, parser_stats: Dict) -> str:
        """Generate extraction statistics report"""
        output_path = self.output_dir / "extraction_stats.txt"
        
        with open(output_path, 'w') as f:
            f.write("Email Extraction Statistics\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            f.write("Summary:\n")
            f.write(f"  Total files processed: {parser_stats.get('total_files', 0)}\n")
            f.write(f"  Successfully parsed: {parser_stats.get('successfully_parsed', 0)}\n")
            f.write(f"  Failed to parse: {parser_stats.get('failed_parse', 0)}\n")
            
            total = parser_stats.get('total_files', 0)
            if total > 0:
                success_rate = (parser_stats.get('successfully_parsed', 0) / total) * 100
                f.write(f"  Success rate: {success_rate:.2f}%\n\n")
            
            f.write("Field Completeness:\n")
            f.write("-" * 60 + "\n")
            for field, stats in sorted(parser_stats.get('field_completeness', {}).items()):
                present = stats.get('present', 0)
                missing = stats.get('missing', 0)
                total_field = present + missing
                if total_field > 0:
                    completeness = (present / total_field) * 100
                    f.write(f"  {field:<20} {present:>8}/{total_field:<8} ({completeness:>6.1f}%)\n")
        
        logger.info(f"Extraction stats: {output_path}")
        return str(output_path)
    
    def generate_error_report(self, parse_errors: list) -> str:
        """Generate error log"""
        output_path = self.output_dir / "error_log.txt"
        
        with open(output_path, 'w') as f:
            f.write("Email Parse Error Log\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"Total errors: {len(parse_errors)}\n\n")
            
            if len(parse_errors) > 0:
                for i, error in enumerate(parse_errors, 1):
                    f.write(f"{i}. {error}\n")
            else:
                f.write("No errors! All emails parsed successfully.\n")
        
        logger.info(f"Error log: {output_path}")
        return str(output_path)
    
    def generate_summary_report(self, parser_stats: Dict, detector_stats: Dict, notification_stats: Dict) -> str:
        """Generate comprehensive summary report"""
        output_path = self.output_dir / "summary_report.txt"
        
        with open(output_path, 'w') as f:
            f.write("Enron Email Pipeline - Summary Report\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            # EXTRACTION PHASE
            f.write("EXTRACTION PHASE\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total files found: {parser_stats.get('total_files', 0)}\n")
            f.write(f"Successfully parsed: {parser_stats.get('successfully_parsed', 0)}\n")
            f.write(f"Parse failures: {parser_stats.get('failed_parse', 0)}\n")
            
            total = parser_stats.get('total_files', 0)
            if total > 0:
                success_rate = (parser_stats.get('successfully_parsed', 0) / total) * 100
                f.write(f"Success rate: {success_rate:.2f}%\n")
            
            f.write("\nDEDUPLICATION PHASE\n")
            f.write("-" * 70 + "\n")
            f.write(f"Duplicate groups found: {detector_stats.get('total_groups', 0)}\n")
            f.write(f"Total duplicates flagged: {detector_stats.get('total_duplicates', 0)}\n")
            if detector_stats.get('total_groups', 0) > 0:
                avg_size = detector_stats.get('avg_group_size', 0)
                f.write(f"Average group size: {avg_size:.2f}\n")
            
            f.write("\nNOTIFICATION PHASE\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total notifications: {notification_stats.get('total_notifications', 0)}\n")
            f.write(f"Sent: {notification_stats.get('sent', 0)}\n")
            f.write(f"Failed: {notification_stats.get('failed', 0)}\n")
            f.write(f"Drafted: {notification_stats.get('drafted', 0)}\n")
            
            if notification_stats.get('errors', []):
                f.write("\nErrors:\n")
                for error in notification_stats.get('errors', []):
                    f.write(f"  - {error}\n")
            
            # Footer
            f.write("\n" + "=" * 70 + "\n")
            f.write("End of Report\n")
        
        logger.info(f"Summary report: {output_path}")
        return str(output_path)
    
    def generate_database_summary(self) -> str:
        """Generate database summary and analytics"""
        output_path = self.output_dir / "database_summary.txt"
        
        total_emails = self.db.get_email_count()
        duplicate_count = self.db.get_duplicate_count()
        
        with open(output_path, 'w') as f:
            f.write("Database Summary\n")
            f.write("=" * 70 + "\n")
            f.write(f"Generated: {datetime.now()}\n\n")
            
            f.write("STATISTICS\n")
            f.write("-" * 70 + "\n")
            f.write(f"Total emails in database: {total_emails}\n")
            f.write(f"Emails marked as duplicates: {duplicate_count}\n")
            
            if total_emails > 0:
                dup_percentage = (duplicate_count / total_emails) * 100
                original_percentage = 100 - dup_percentage
                f.write(f"Original emails: {total_emails - duplicate_count}\n")
                f.write(f"Duplicate percentage: {dup_percentage:.2f}%\n")
                f.write(f"Original percentage: {original_percentage:.2f}%\n")
            
            # Top senders
            f.write("\nTOP SENDERS\n")
            f.write("-" * 70 + "\n")
            query = """
                SELECT from_address, COUNT(*) as email_count
                FROM emails
                WHERE is_duplicate = 0
                GROUP BY from_address
                ORDER BY email_count DESC
                LIMIT 15
            """
            try:
                senders = self.db.execute_query(query)
                if senders:
                    f.write(f"{'Sender':<40} {'Email Count':>15}\n")
                    f.write("-" * 70 + "\n")
                    for sender in senders:
                        sender_addr = sender.get('from_address', 'Unknown')[:40]
                        count = sender.get('email_count', 0)
                        f.write(f"{sender_addr:<40} {count:>15}\n")
                else:
                    f.write("No senders found.\n")
            except Exception as e:
                logger.warning(f"Could not get top senders: {str(e)}")
                f.write(f"Error retrieving senders: {str(e)}\n")
            
            # Duplicate summary
            f.write("\nDUPLICATE SUMMARY\n")
            f.write("-" * 70 + "\n")
            try:
                dup_groups = self.db.get_duplicate_groups()
                if dup_groups:
                    f.write(f"Total duplicate groups: {len(dup_groups)}\n")
                    
                    # Group size distribution
                    size_dist = {}
                    for group in dup_groups:
                        size = group.get('group_size', 0)
                        size_dist[size] = size_dist.get(size, 0) + 1
                    
                    f.write("\nGroup Size Distribution:\n")
                    for size in sorted(size_dist.keys()):
                        count = size_dist[size]
                        f.write(f"  Size {size}: {count} groups\n")
                else:
                    f.write("No duplicate groups found.\n")
            except Exception as e:
                logger.warning(f"Could not get duplicate groups: {str(e)}")
                f.write(f"Error retrieving duplicates: {str(e)}\n")
            
            f.write("\n" + "=" * 70 + "\n")
            f.write("End of Report\n")
        
        logger.info(f"Database summary: {output_path}")
        return str(output_path)