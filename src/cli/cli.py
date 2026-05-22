"""
CLI interface for internship automation tool
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from src.profile.cv_manager import ProfileManager, CVProfile, Education, Experience
from src.database.db_manager import ApplicationDatabase


class CLIInterface:
    """Command-line interface for the application"""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.db = ApplicationDatabase()
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser"""
        parser = argparse.ArgumentParser(
            description='Internship Application Automation Tool',
            epilog='For more info: https://github.com/your-repo/internship-auto-apply'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Init command - setup and create CV template
        init_parser = subparsers.add_parser('init', help='Initialize and setup CV')
        
        # Config command - manage CV and filters
        config_parser = subparsers.add_parser('config', help='Manage CV and filter configurations')
        config_parser.add_argument('action', choices=['view', 'edit', 'add-education', 'add-experience'])
        config_parser.add_argument('--education-degree', type=str, help='Degree (for add-education)')
        config_parser.add_argument('--education-field', type=str, help='Field of study')
        config_parser.add_argument('--education-university', type=str, help='University name')
        config_parser.add_argument('--education-year', type=int, help='Graduation year')
        
        # Search command - search for internships (placeholder for now)
        search_parser = subparsers.add_parser('search', help='Search for internships')
        search_parser.add_argument('--country', type=str, default='Spain', help='Country to search in')
        search_parser.add_argument('--city', type=str, help='City to search in')
        search_parser.add_argument('--role', type=str, help='Job title/position')
        search_parser.add_argument('--keywords', type=str, help='Keywords (comma-separated)')
        search_parser.add_argument('--exclude', type=str, help='Exclude keywords (comma-separated)')
        search_parser.add_argument('--level', choices=['entry', 'mid', 'senior'], help='Experience level')
        search_parser.add_argument('--save-filter', type=str, help='Save this search as a filter')
        
        # Status command - view applications and stats
        status_parser = subparsers.add_parser('status', help='View application status and statistics')
        status_parser.add_argument('--filter', type=str, help='Filter by status (pending, submitted, etc.)')
        status_parser.add_argument('--limit', type=int, default=10, help='Limit number of results')
        
        # Submit command - submit pending application
        submit_parser = subparsers.add_parser('submit', help='Submit a pending application')
        submit_parser.add_argument('app_id', type=int, help='Application ID to submit')
        
        return parser
    
    def run(self, args: Optional[list] = None):
        """Parse and execute commands"""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return
        
        # Route to appropriate command handler
        command_method = getattr(self, f'cmd_{parsed_args.command}', None)
        if command_method:
            command_method(parsed_args)
        else:
            print(f"Unknown command: {parsed_args.command}")
    
    def cmd_init(self, args):
        """Initialize and setup CV"""
        print("\n🚀 Initializing Internship Application Tool...\n")
        
        # Load or create CV
        cv = self.profile_manager.load_cv()
        
        # Validate and show warnings
        is_valid, warnings = self.profile_manager.validate_cv(cv)
        
        if warnings:
            print("⚠️  Validation Warnings:")
            for warning in warnings:
                print(f"  {warning}")
        
        # Initialize database
        print("\n📊 Initializing database...")
        stats = self.db.get_application_stats()
        print(f"✓ Database ready")
        
        print("\n✅ Setup complete!")
        print("\nNext steps:")
        print("  1. Edit your CV: config/cv_template.json")
        print("  2. Search for internships: python src/main.py search --country Spain --role 'Developer'")
        print("  3. View applications: python src/main.py status")
    
    def cmd_config(self, args):
        """Manage CV and filter configurations"""
        cv = self.profile_manager.load_cv()
        
        if args.action == 'view':
            print("\n📄 Current CV Profile:")
            print(f"Name: {cv.name}")
            print(f"Email: {cv.email}")
            print(f"Phone: {cv.phone}")
            print(f"Location: {cv.location}, {cv.country}")
            print(f"Summary: {cv.summary}")
            print(f"\nSkills: {', '.join(cv.skills)}")
            print(f"Languages: {', '.join([f'{lang} ({level})' for lang, level in cv.languages.items()])}")
            
            if cv.education:
                print(f"\nEducation:")
                for edu in cv.education:
                    print(f"  - {edu.degree} in {edu.field}, {edu.university} ({edu.graduation_year})")
            
            if cv.experience:
                print(f"\nExperience:")
                for exp in cv.experience:
                    print(f"  - {exp.position} at {exp.company} ({exp.duration_months} months)")
        
        elif args.action == 'edit':
            print("\n📝 Edit config file: config/cv_template.json")
            print("  Opening in default editor... (manual edit required)")
        
        elif args.action == 'add-education':
            if not all([args.education_degree, args.education_field, args.education_university, args.education_year]):
                print("Error: Please provide --education-degree, --education-field, --education-university, --education-year")
                return
            
            education = Education(
                degree=args.education_degree,
                field=args.education_field,
                university=args.education_university,
                graduation_year=args.education_year
            )
            cv = self.profile_manager.add_education(cv, education)
            self.profile_manager.save_cv(cv)
            print(f"✓ Education added: {education.degree} in {education.field}")
    
    def cmd_search(self, args):
        """Search for internships (placeholder)"""
        print("\n🔍 Searching for internships...")
        print(f"  Country: {args.country}")
        if args.city:
            print(f"  City: {args.city}")
        if args.role:
            print(f"  Role: {args.role}")
        if args.keywords:
            print(f"  Keywords: {args.keywords}")
        
        print("\n⏳ Job board integration coming in Phase 2...")
        print("  - LinkedIn scraper")
        print("  - Indeed scraper")
        print("  - Glassdoor scraper")
    
    def cmd_status(self, args):
        """View application status and statistics"""
        print("\n📊 Application Statistics:")
        stats = self.db.get_application_stats()
        print(f"  Total: {stats.get('total', 0)}")
        print(f"  Pending: {stats.get('pending', 0)}")
        print(f"  Submitted: {stats.get('submitted', 0)}")
        print(f"  Rejected: {stats.get('rejected', 0)}")
        
        # Get pending applications
        pending = self.db.get_pending_applications(limit=args.limit)
        if pending:
            print(f"\n📋 Pending Applications ({len(pending)}):")
            for app in pending:
                print(f"  [{app['id']}] {app['position']} at {app['company']} ({app['location']}, {app['country']})")
        else:
            print("\n✓ No pending applications")
    
    def cmd_submit(self, args):
        """Submit a pending application"""
        print(f"\n📤 Submitting application ID {args.app_id}...")
        
        success = self.db.update_application_status(args.app_id, 'submitted', 'Submitted via CLI')
        if success:
            print(f"✓ Application {args.app_id} marked as submitted")
        else:
            print(f"✗ Application {args.app_id} not found")


def main():
    """Main entry point"""
    cli = CLIInterface()
    cli.run()


if __name__ == '__main__':
    main()