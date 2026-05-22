"""
Glassdoor job scraper
Searches and extracts internship job postings from Glassdoor
"""
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class GlassdoorScraper:
    """Scrapes Glassdoor for internship job postings"""
    
    BASE_URL = "https://www.glassdoor.es/Empleos/internship"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    def __init__(self, request_timeout: int = 10):
        """
        Initialize Glassdoor scraper
        
        Args:
            request_timeout: Request timeout in seconds
        """
        self.request_timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def search_internships(
        self,
        country: str = "Spain",
        cities: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for internship positions on Glassdoor
        
        Args:
            country: Country to search in
            cities: List of cities to filter by
            keywords: Job title/keywords to search for
            exclude_keywords: Keywords to exclude
            max_results: Maximum number of results
        
        Returns:
            List of job postings with metadata
        """
        jobs = []
        
        try:
            # Build search URL
            search_query = "internship"
            if keywords:
                search_query = " ".join(keywords[:2])
            
            location_filter = self._build_location_filter(cities)
            
            url = self._build_search_url(search_query, location_filter)
            logger.info(f"Searching Glassdoor: {url}")
            
            # Fetch and parse results
            jobs = self._fetch_and_parse(
                url,
                exclude_keywords=exclude_keywords,
                max_results=max_results
            )
            
            logger.info(f"✓ Found {len(jobs)} internship postings")
            
        except Exception as e:
            logger.error(f"✗ Search error: {str(e)}")
        
        return jobs
    
    def _build_location_filter(self, cities: Optional[List[str]]) -> str:
        """Build location filter"""
        if cities:
            return ",".join(cities)
        return ""
    
    def _build_search_url(self, query: str, location_filter: str) -> str:
        """Build Glassdoor search URL"""
        # Use Glassdoor Spain site
        url = f"{self.BASE_URL}-{query.replace(' ', '-')}"
        
        if location_filter:
            url += f"_L1A{location_filter.replace(' ', '')}"
        
        return url
    
    def _fetch_and_parse(
        self,
        url: str,
        exclude_keywords: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """Fetch and parse job listings"""
        jobs = []
        exclude_keywords = exclude_keywords or []
        
        try:
            response = self.session.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            # Glassdoor uses complex JavaScript, so direct scraping is limited
            # Look for job listings in the page
            job_listings = soup.find_all("div", class_="JobCard_jobCardContainer")
            
            if not job_listings:
                # Try alternative selectors
                job_listings = soup.find_all("div", {"data-test": "jobListing"})
            
            logger.info(f"Found {len(job_listings)} job listings")
            
            for listing in job_listings:
                if len(jobs) >= max_results:
                    break
                
                job_data = self._parse_job_listing(listing)
                
                if job_data and not self._contains_exclude_keywords(job_data, exclude_keywords):
                    jobs.append(job_data)
                    logger.info(f"✓ [{len(jobs)}] {job_data['position']} at {job_data['company']}")
            
        except Exception as e:
            logger.error(f"Error fetching Glassdoor: {str(e)}")
        
        return jobs
    
    def _parse_job_listing(self, listing) -> Optional[Dict[str, Any]]:
        """Parse individual job listing"""
        try:
            # Extract position
            position_elem = listing.find("a", class_="JobCard_jobTitle")
            if not position_elem:
                position_elem = listing.find("h2")
            position = position_elem.get_text(strip=True) if position_elem else "Unknown"
            
            # Extract company
            company_elem = listing.find("div", class_="EmployerName")
            if not company_elem:
                company_elem = listing.find("span", class_="JobCard_companyName")
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Extract location
            location_elem = listing.find("div", class_="JobCard_location")
            location_text = location_elem.get_text(strip=True) if location_elem else "Spain"
            
            country, city = self._parse_location(location_text)
            
            # Extract job URL
            job_url = ""
            link_elem = listing.find("a", class_="JobCard_jobTitle")
            if link_elem and link_elem.get("href"):
                job_url = link_elem.get("href")
                if not job_url.startswith("http"):
                    job_url = f"https://www.glassdoor.es{job_url}"
            
            # Extract description/snippet
            snippet_elem = listing.find("div", class_="JobCard_snippet")
            description = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            job_data = {
                "job_id": f"gd_{hash(job_url) % 10**8}",
                "platform": "Glassdoor",
                "company": company,
                "position": position,
                "location": city or location_text,
                "country": country,
                "job_url": job_url,
                "description": description[:1000],
                "salary": None,
                "posted_date": datetime.now().strftime("%Y-%m-%d"),
                "employment_type": "Internship",
                "scraped_at": datetime.now().isoformat()
            }
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Error parsing job listing: {str(e)}")
            return None
    
    def _parse_location(self, location_str: str) -> tuple[str, str]:
        """Parse location string"""
        if not location_str:
            return "Spain", "Unknown"
        
        parts = location_str.split(",")
        city = parts[0].strip() if len(parts) > 0 else location_str
        country = parts[-1].strip() if len(parts) > 1 else "Spain"
        
        return country, city
    
    def _contains_exclude_keywords(self, job_data: Dict, exclude_keywords: List[str]) -> bool:
        """Check if job contains any exclude keywords"""
        if not exclude_keywords:
            return False
        
        searchable = (job_data.get("position", "") + " " + job_data.get("description", "")).lower()
        
        for keyword in exclude_keywords:
            if keyword.lower() in searchable:
                return True
        
        return False
    
    def save_jobs_to_db(self, jobs: List[Dict], db_manager) -> int:
        """Save scraped jobs to database"""
        count = 0
        for job in jobs:
            app_id = db_manager.add_application(job)
            if app_id:
                count += 1
        
        logger.info(f"✓ Saved {count} new jobs to database")
        return count


def scrape_glassdoor_internships(
    country: str = "Spain",
    cities: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    exclude_keywords: Optional[List[str]] = None,
    max_results: int = 25,
    db_manager=None
) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape Glassdoor internships
    
    Args:
        country: Country to search in
        cities: List of cities
        keywords: Job keywords
        exclude_keywords: Keywords to exclude
        max_results: Maximum results
        db_manager: Database manager to save results
    
    Returns:
        List of job postings
    """
    scraper = GlassdoorScraper()
    
    try:
        jobs = scraper.search_internships(
            country=country,
            cities=cities,
            keywords=keywords,
            exclude_keywords=exclude_keywords,
            max_results=max_results
        )
        
        if db_manager and jobs:
            scraper.save_jobs_to_db(jobs, db_manager)
        
        return jobs
    
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        return []


if __name__ == "__main__":
    # Test the scraper
    jobs = scrape_glassdoor_internships(
        country="Spain",
        cities=["Madrid"],
        keywords=["Developer"],
        max_results=10
    )
    
    print(f"\n✓ Found {len(jobs)} internships")
    for job in jobs:
        print(f"\n  {job['position']}")
        print(f"  @ {job['company']} ({job['location']})")
