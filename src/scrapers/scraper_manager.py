"""
Unified scraper manager
Orchestrates multiple job board scrapers
"""
import logging
from typing import List, Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from src.scrapers.linkedin_scraper import LinkedInScraper
from src.scrapers.indeed_scraper import IndeedScraper
from src.scrapers.glassdoor_scraper import GlassdoorScraper

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ScraperManager:
    """Manages and orchestrates multiple job board scrapers"""
    
    def __init__(self, db_manager=None):
        """
        Initialize scraper manager
        
        Args:
            db_manager: Database manager for saving results
        """
        self.db_manager = db_manager
        self.linkedin = LinkedInScraper(headless=True)
        self.indeed = IndeedScraper()
        self.glassdoor = GlassdoorScraper()
    
    def search_all_platforms(
        self,
        country: str = "Spain",
        cities: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        max_results_per_platform: int = 20,
        platforms: Optional[List[str]] = None,
        use_threads: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search all job platforms for internships
        
        Args:
            country: Country to search in
            cities: List of cities
            keywords: Job keywords
            exclude_keywords: Keywords to exclude
            max_results_per_platform: Max results per platform
            platforms: Specific platforms to search (default: all)
            use_threads: Use threading for parallel searches
        
        Returns:
            Dictionary with results by platform
        """
        if platforms is None:
            platforms = ["linkedin", "indeed", "glassdoor"]
        
        logger.info(f"🔍 Searching for internships on: {', '.join(platforms)}")
        logger.info(f"   Location: {', '.join(cities or [country])}")
        logger.info(f"   Keywords: {', '.join(keywords or ['internship'])}")
        
        results = {}
        
        if use_threads:
            results = self._search_parallel(
                country, cities, keywords, exclude_keywords,
                max_results_per_platform, platforms
            )
        else:
            results = self._search_sequential(
                country, cities, keywords, exclude_keywords,
                max_results_per_platform, platforms
            )
        
        return results
    
    def _search_parallel(
        self,
        country: str,
        cities: Optional[List[str]],
        keywords: Optional[List[str]],
        exclude_keywords: Optional[List[str]],
        max_results: int,
        platforms: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search multiple platforms in parallel"""
        results = {}
        
        def search_platform(platform: str):
            try:
                logger.info(f"  [Start] {platform.upper()}")
                
                if platform.lower() == "linkedin":
                    jobs = self.linkedin.search_internships(
                        country=country,
                        cities=cities,
                        keywords=keywords,
                        exclude_keywords=exclude_keywords,
                        max_results=max_results
                    )
                
                elif platform.lower() == "indeed":
                    jobs = self.indeed.search_internships(
                        country="ES" if country == "Spain" else country,
                        cities=cities,
                        keywords=keywords,
                        exclude_keywords=exclude_keywords,
                        max_results=max_results
                    )
                
                elif platform.lower() == "glassdoor":
                    jobs = self.glassdoor.search_internships(
                        country=country,
                        cities=cities,
                        keywords=keywords,
                        exclude_keywords=exclude_keywords,
                        max_results=max_results
                    )
                else:
                    jobs = []
                
                logger.info(f"  [Done] {platform.upper()}: {len(jobs)} results")
                return platform, jobs
            
            except Exception as e:
                logger.error(f"  [Error] {platform.upper()}: {str(e)}")
                return platform, []
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(search_platform, platform): platform
                for platform in platforms
            }
            
            for future in as_completed(futures):
                platform, jobs = future.result()
                results[platform] = jobs
                
                # Save to database if available
                if self.db_manager and jobs:
                    count = 0
                    for job in jobs:
                        app_id = self.db_manager.add_application(job)
                        if app_id:
                            count += 1
                    logger.info(f"  ✓ Saved {count} jobs from {platform} to database")
        
        return results
    
    def _search_sequential(
        self,
        country: str,
        cities: Optional[List[str]],
        keywords: Optional[List[str]],
        exclude_keywords: Optional[List[str]],
        max_results: int,
        platforms: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search platforms sequentially"""
        results = {}
        
        for platform in platforms:
            try:
                logger.info(f"  Searching {platform.upper()}...")
                
                if platform.lower() == "linkedin":
                    jobs = self.linkedin.search_internships(
                        country=country,
                        cities=cities,
                        keywords=keywords,
                        exclude_keywords=exclude_keywords,
                        max_results=max_results
                    )
                
                elif platform.lower() == "indeed":
                    jobs = self.indeed.search_internships(
                        country="ES" if country == "Spain" else country,
                        cities=cities,
                        keywords=keywords,
                        exclude_keywords=exclude_keywords,
                        max_results=max_results
                    )
                
                elif platform.lower() == "glassdoor":
                    jobs = self.glassdoor.search_internships(
                        country=country,
                        cities=cities,
                        keywords=keywords,
                        exclude_keywords=exclude_keywords,
                        max_results=max_results
                    )
                else:
                    jobs = []
                
                results[platform] = jobs
                logger.info(f"  ✓ {platform.upper()}: {len(jobs)} results")
                
                # Save to database
                if self.db_manager and jobs:
                    count = 0
                    for job in jobs:
                        app_id = self.db_manager.add_application(job)
                        if app_id:
                            count += 1
                    logger.info(f"    → Saved {count} jobs to database")
                
                time.sleep(2)  # Rate limiting between platforms
            
            except Exception as e:
                logger.error(f"  ✗ {platform.upper()} failed: {str(e)}")
                results[platform] = []
        
        return results
    
    def get_summary(self, results: Dict[str, List[Dict[str, Any]]]) -> str:
        """Generate summary of search results"""
        total = sum(len(jobs) for jobs in results.values())
        
        summary = f"\n📊 Search Summary:\n"
        summary += f"{'='*50}\n"
        
        for platform, jobs in results.items():
            summary += f"{platform.upper():<12} {len(jobs):>3} internships\n"
        
        summary += f"{'='*50}\n"
        summary += f"{'TOTAL':<12} {total:>3} internships\n"
        
        return summary
    
    def close(self):
        """Close all scrapers"""
        try:
            self.linkedin.close()
        except:
            pass


def search_internships(
    country: str = "Spain",
    cities: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    exclude_keywords: Optional[List[str]] = None,
    max_results: int = 20,
    db_manager=None,
    platforms: Optional[List[str]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Main function to search internships across all platforms
    
    Args:
        country: Country to search
        cities: List of cities
        keywords: Job keywords
        exclude_keywords: Keywords to exclude
        max_results: Max results per platform
        db_manager: Database manager
        platforms: Which platforms to search
    
    Returns:
        Results by platform
    """
    manager = ScraperManager(db_manager=db_manager)
    
    try:
        results = manager.search_all_platforms(
            country=country,
            cities=cities,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            max_results_per_platform=max_results,
            platforms=platforms,
            use_threads=False  # Sequential for stability
        )
        
        print(manager.get_summary(results))
        return results
    
    finally:
        manager.close()


if __name__ == "__main__":
    # Test the manager
    results = search_internships(
        country="Spain",
        cities=["Madrid"],
        keywords=["Python", "Data"],
        max_results=5
    )
