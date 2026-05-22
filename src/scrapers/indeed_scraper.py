"""
Indeed job scraper
Searches and extracts internship job postings from Indeed
"""
import logging
import time
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class IndeedScraper:
    """Scrapes Indeed for internship job postings"""
    
    BASE_URL = "https://www.indeed.com/jobs"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    def __init__(self, request_timeout: int = 10, retry_count: int = 3):
        """
        Initialize Indeed scraper
        
        Args:
            request_timeout: Request timeout in seconds
            retry_count: Number of retries for failed requests
        """
        self.request_timeout = request_timeout
        self.retry_count = retry_count
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def search_internships(
        self,
        country: str = "ES",
        cities: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for internship positions on Indeed
        
        Args:
            country: Country code (ES for Spain)
            cities: List of cities to filter by
            keywords: Job title/keywords to search for
            exclude_keywords: Keywords to exclude
            max_results: Maximum number of results
        
        Returns:
            List of job postings with metadata
        """
        jobs = []
        search_query = "internship"
        
        if keywords:
            search_query = " ".join(keywords[:2])
        
        try:
            # Build search parameters
            location_param = self._build_location_param(country, cities)
            
            url = self._build_search_url(
                query=search_query,
                location=location_param
            )
            
            logger.info(f"Searching Indeed: {search_query} in {location_param}")
            
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
    
    def _build_location_param(self, country: str, cities: Optional[List[str]]) -> str:
        """Build location parameter for search"""
        if cities:
            return ", ".join(cities)
        
        country_map = {
            "ES": "Spain",
            "Spain": "Spain",
            "FR": "France",
            "France": "France",
            "DE": "Germany",
            "Germany": "Germany",
            "IT": "Italy",
            "Italy": "Italy"
        }
        
        return country_map.get(country, "Spain")
    
    def _build_search_url(self, query: str, location: str) -> str:
        """Build Indeed search URL"""
        params = {
            "q": query,
            "l": location,
            "jt": "internship",
            "sort": "date"
        }
        
        return f"{self.BASE_URL}?{urlencode(params)}"
    
    def _fetch_and_parse(
        self,
        url: str,
        exclude_keywords: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """Fetch and parse job listings from Indeed"""
        jobs = []
        exclude_keywords = exclude_keywords or []
        start = 0
        
        while len(jobs) < max_results:
            try:
                # Add pagination
                paginated_url = f"{url}&start={start}"
                
                response = self._make_request(paginated_url)
                if not response:
                    break
                
                soup = BeautifulSoup(response.content, "html.parser")
                
                # Find all job cards
                job_cards = soup.find_all("div", class_="job_seen_beacon")
                
                if not job_cards:
                    logger.warning("No job cards found on page")
                    break
                
                logger.info(f"Found {len(job_cards)} cards on page (start={start})")
                
                for card in job_cards:
                    if len(jobs) >= max_results:
                        break
                    
                    job_data = self._parse_job_card(card)
                    
                    if job_data and not self._contains_exclude_keywords(job_data, exclude_keywords):
                        jobs.append(job_data)
                        logger.info(f"✓ [{len(jobs)}] {job_data['position']} at {job_data['company']}")
                
                # Check if we found all cards on this page
                if len(job_cards) < 15:  # Typically ~15 results per page
                    logger.info("Reached end of results")
                    break
                
                start += len(job_cards)
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error parsing page: {str(e)}")
                break
        
        return jobs
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with retry logic"""
        for attempt in range(self.retry_count):
            try:
                response = self.session.get(url, timeout=self.request_timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.retry_count}): {str(e)}")
                if attempt < self.retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        
        return None
    
    def _parse_job_card(self, card) -> Optional[Dict[str, Any]]:
        """Parse individual job card"""
        try:
            # Extract job ID
            job_id = card.get("data-jk", "unknown")
            
            # Get job title
            title_elem = card.find("h2", class_="jobTitle")
            if not title_elem:
                title_elem = card.find("a", class_="jcs-JobTitle")
            position = title_elem.get_text(strip=True) if title_elem else "Unknown"
            
            # Get company
            company_elem = card.find("span", class_="companyName")
            company = company_elem.get_text(strip=True) if company_elem else "Unknown"
            
            # Get location
            location_elem = card.find("span", class_="companyLocation")
            location_text = location_elem.get_text(strip=True) if location_elem else "Unknown"
            
            country, city = self._parse_location(location_text)
            
            # Get job URL
            link_elem = card.find("a", class_="jcs-JobTitle")
            if not link_elem:
                link_elem = title_elem
            
            job_url = ""
            if link_elem and link_elem.get("href"):
                job_url = link_elem.get("href")
                if not job_url.startswith("http"):
                    job_url = f"https://www.indeed.com{job_url}"
            
            # Get description snippet
            snippet_elem = card.find("div", class_="job-snippet")
            description = ""
            if snippet_elem:
                description_parts = snippet_elem.find_all("ul")
                if description_parts:
                    description = "\n".join([li.get_text(strip=True) for li in description_parts[0].find_all("li")])
            
            # Get posted date
            posted_date = self._extract_posted_date(card)
            
            # Get salary if available
            salary = self._extract_salary(card)
            
            job_data = {
                "job_id": f"ind_{job_id}",
                "platform": "Indeed",
                "company": company.replace("company reviews", "").strip(),
                "position": position,
                "location": city or location_text,
                "country": country,
                "job_url": job_url,
                "description": description[:1000],
                "salary": salary,
                "posted_date": posted_date,
                "posted_date_formatted": posted_date,
                "employment_type": "Internship",
                "scraped_at": datetime.now().isoformat()
            }
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Error parsing job card: {str(e)}")
            return None
    
    def _parse_location(self, location_str: str) -> tuple[str, str]:
        """Parse location string"""
        if not location_str:
            return "Spain", "Unknown"
        
        parts = location_str.split(",")
        city = parts[0].strip() if len(parts) > 0 else location_str
        country = parts[-1].strip() if len(parts) > 1 else "Spain"
        
        return country, city
    
    def _extract_posted_date(self, card) -> str:
        """Extract posted date"""
        try:
            date_elem = card.find("span", class_="date")
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                
                # Parse relative dates like "2 days ago"
                if "day" in date_text.lower():
                    days = int(date_text.split()[0])
                    date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                    return date
                elif "hour" in date_text.lower():
                    return datetime.now().strftime("%Y-%m-%d")
                else:
                    return date_text
        except:
            pass
        
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_salary(self, card) -> Optional[str]:
        """Extract salary information if available"""
        try:
            salary_elem = card.find("span", class_="salary-snippet")
            if salary_elem:
                return salary_elem.get_text(strip=True)
        except:
            pass
        
        return None
    
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


def scrape_indeed_internships(
    country: str = "ES",
    cities: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    exclude_keywords: Optional[List[str]] = None,
    max_results: int = 25,
    db_manager=None
) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape Indeed internships
    
    Args:
        country: Country code (ES, FR, DE, IT)
        cities: List of cities
        keywords: Job keywords
        exclude_keywords: Keywords to exclude
        max_results: Maximum results
        db_manager: Database manager to save results
    
    Returns:
        List of job postings
    """
    scraper = IndeedScraper()
    
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
    jobs = scrape_indeed_internships(
        country="ES",
        cities=["Madrid", "Barcelona"],
        keywords=["Python", "Data"],
        max_results=10
    )
    
    print(f"\n✓ Found {len(jobs)} internships")
    for job in jobs:
        print(f"\n  {job['position']}")
        print(f"  @ {job['company']} ({job['location']})")
        print(f"  URL: {job['job_url']}")
