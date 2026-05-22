"""
CLI interface for internship automation tool with filtering support
"""
import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from src.profile.cv_manager import ProfileManager, CVProfile, Education, Experience
from src.database.db_manager import ApplicationDatabase
from src.scrapers.scraper_manager import search_internships
from src.filters.filter_engine import FilterEngine, apply_filters


class CLIInterface:
    """Command-line interface for the application"""
    
    def __init__(self):
        self.profile_manager = ProfileManager()
        self.db = ApplicationDatabase()
        self.filter_engine = FilterEngine()
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
        
        # Search command - search for internships
        search_parser = subparsers.add_parser('search', help='Search for internships')
        search_parser.add_argument('--country', type=str, default='Spain', help='Country to search in')
        search_parser.add_argument('--city', type=str, action='append', dest='cities', help='City to search in (can use multiple)')
        search_parser.add_argument('--role', type=str, help='Job title/position')
        search_parser.add_argument('--keywords', type=str, help='Keywords (comma-separated)')
        search_parser.add_argument('--exclude', type=str, help='Exclude keywords (comma-separated)')
        search_parser.add_argument('--languages', type=str, help='Required languages (comma-separated)')
        search_parser.add_argument('--min-hours', type=int, help='Minimum hours per week')
        search_parser.add_argument('--max-hours', type=int, help='Maximum hours per week')
        search_parser.add_argument('--remote', choices=['remote', 'hybrid', 'on-site'], help='Remote preference')
        search_parser.add_argument('--paid', action='store_true', help='Only paid internships')
        search_parser.add_argument('--level', choices=['entry', 'mid', 'senior'], help='Experience level')
        search_parser.add_argument('--max-results', type=int, default=20, help='Max results per platform')
        search_parser.add_argument('--platform', type=str, action='append', dest='platforms', 
                                  choices=['linkedin', 'indeed', 'glassdoor'],
                                  help='Specific platform to search (default: all)')
        search_parser.add_argument('--save-filter', type=str, help='Save this search as a filter')
        search_parser.add_argument('--no-save-db', action='store_true', help='Do not save results to database')
        search_parser.add_argument('--threshold', type=int, default=50, help='Match score threshold (0-100)')
        search_parser.add_argument('--apply-filter', action='store_true', help='Apply advanced filtering')
        
        # Filter command - apply filters to existing jobs
        filter_parser = subparsers.add_parser('filter', help='Apply filters to job database')
        filter_parser.add_argument('--country', type=str, help='Filter by country')
        filter_parser.add_argument('--city', type=str, action='append', dest='cities', help='Filter by city')
        filter_parser.add_argument('--languages', type=str, help='Required languages (comma-separated)')
        filter_parser.add_argument('--remote', choices=['remote', 'hybrid', 'on-site'], help='Remote type')
        filter_parser.add_argument('--paid', action='store_true', help='Only paid internships')
        filter_parser.add_argument('--min-hours', type=int, help='Minimum hours per week')
        filter_parser.add_argument('--max-hours', type=int, help='Maximum hours per week')
        filter_parser.add_argument('--threshold', type=int, default=50, help='Match score threshold')
        filter_parser.add_argument('--limit', type=int, default=20, help='Limit results')
        filter_parser.add_argument('--sort', choices=['score', 'company', 'date'], default='score', help='Sort by')
        
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
        print("  3. Filter results: python src/main.py filter --languages English --remote hybrid")
        print("  4. View applications: python src/main.py status")
    
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
        """Search for internships across multiple platforms"""
        print("\n🔍 Starting internship search...\n")
        
        # Prepare search parameters
        keywords = None
        if args.role or args.keywords:
            keywords = []
            if args.role:
                keywords.append(args.role)
            if args.keywords:
                keywords.extend([k.strip() for k in args.keywords.split(",")])
        
        exclude_keywords = None
        if args.exclude:
            exclude_keywords = [k.strip() for k in args.exclude.split(",")]
        
        cities = args.cities or []
        platforms = args.platforms or ["linkedin", "indeed", "glassdoor"]
        
        try:
            # Perform search across platforms
            results = search_internships(
                country=args.country,
                cities=cities if cities else None,
                keywords=keywords,
                exclude_keywords=exclude_keywords,
                max_results=args.max_results,
                db_manager=self.db if not args.no_save_db else None,
                platforms=platforms
            )
            
            # Save filter if requested
            if args.save_filter:
                languages = [l.strip() for l in args.languages.split(",")] if args.languages else []
                filter_config = {
                    "name": args.save_filter,
                    "country": args.country,
                    "cities": cities,
                    "positions": keywords or [],
                    "keywords": keywords or [],
                    "exclude_keywords": exclude_keywords or [],
                    "required_languages": languages,
                    "remote_type": args.remote,
                    "paid_only": args.paid,
                    "experience_level": args.level,
                    "match_threshold": args.threshold
                }
                self.db.save_filter(filter_config)
                print(f"\n✓ Filter '{args.save_filter}' saved")
            
            # Optionally apply filtering
            if args.apply_filter:
                print("\n📊 Applying advanced filters...")
                pending = self.db.get_pending_applications(limit=1000)
                
                languages = [l.strip() for l in args.languages.split(",")] if args.languages else ["English", "Spanish"]
                
                matches = apply_filters(
                    pending,
                    countries=[args.country],
                    cities=cities if cities else None,
                    required_languages=languages,
                    remote_preference=args.remote,
                    exclude_keywords=exclude_keywords,
                    match_threshold=args.threshold
                )
                
                print(f"\n✓ Found {len(matches)} matching internships:\n")
                for match in matches[:10]:
                    print(f"  [{match.match_score}%] {match.job_title} @ {match.company}")
                    print(f"      {', '.join(match.matched_criteria)}")
            else:
                # Show status after search
                print("\n📋 Recent pending applications:")
                pending = self.db.get_pending_applications(limit=5)
                if pending:
                    for app in pending:
                        print(f"  [{app['id']}] {app['position']} @ {app['company']} ({app['location']})")
                else:
                    print("  No pending applications")
            
        except Exception as e:
            print(f"\n✗ Search failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def cmd_filter(self, args):
        """Apply advanced filters to database"""
        print("\n🔍 Applying filters to job database...\n")
        
        try:
            # Get all pending jobs from database
            pending = self.db.get_pending_applications(limit=1000)
            print(f"Found {len(pending)} pending jobs to filter")
            
            # Prepare filter criteria
            languages = [l.strip() for l in args.languages.split(",")] if args.languages else ["English", "Spanish"]
            
            # Apply filters
            matches = apply_filters(
                pending,
                countries=[args.country] if args.country else ["Spain"],
                cities=args.cities,
                required_languages=languages,
                remote_preference=args.remote,
                match_threshold=args.threshold
            )
            
            print(f"\n✓ Found {len(matches)} matching internships\n")
            print("📋 Top Matches:")
            print("="*80)
            
            # Sort results
            if args.sort == 'company':
                matches.sort(key=lambda x: x.company)
            elif args.sort == 'date':
                matches.sort(key=lambda x: x.job_id, reverse=True)
            # Default sort is by score (already sorted)
            
            # Display results
            for i, match in enumerate(matches[:args.limit], 1):
                print(f"\n[{i}] [{match.match_score}%] {match.job_title}")
                print(f"    Company: {match.company}")
                print(f"    Match: {', '.join(match.matched_criteria)}")
                
                # Show language info
                if match.job_requirements.languages:
                    print(f"    Languages: {', '.join(match.job_requirements.languages)}")
                if match.job_requirements.hours_per_week:
                    print(f"    Hours: {match.job_requirements.hours_per_week}h/week ({match.job_requirements.hours_type})")
                if match.job_requirements.remote_type != "unknown":
                    print(f"    Remote: {match.job_requirements.remote_type}")
                if match.notes:
                    print(f"    Notes: {match.notes}")
            
        except Exception as e:
            print(f"\n✗ Filtering failed: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
                print(f"  [{app['id']}] {app['position']} at {app['company']}")
                print(f"       Location: {app['location']}, {app['country']}")
                if app['languages']:
                    print(f"       Languages: {app['languages']}")
                if app['hours_per_week']:
                    print(f"       Hours: {app['hours_per_week']}h/week")
                if app['remote_type']:
                    print(f"       Remote: {app['remote_type']}")
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
