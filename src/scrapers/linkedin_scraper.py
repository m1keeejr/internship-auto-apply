"""
LinkedIn job scraper
Searches and extracts internship job postings from LinkedIn
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scrapes LinkedIn for internship job postings"""
    
    BASE_URL = "https://www.linkedin.com/jobs/search"
    
    def __init__(self, headless: bool = False, implicit_wait: int = 10):
        """
        Initialize LinkedIn scraper
        
        Args:
            headless: Run browser in headless mode
            implicit_wait: Implicit wait time for elements (seconds)
        """
        self.headless = headless
        self.implicit_wait = implicit_wait
        self.driver = None
        self.wait = None
    
    def _setup_driver(self):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(self.implicit_wait)
        self.wait = WebDriverWait(self.driver, 15)
        logger.info("✓ Chrome driver initialized")
    
    def close(self):
        """Close browser driver"""
        if self.driver:
            self.driver.quit()
            logger.info("✓ Driver closed")
    
    def search_internships(
        self,
        country: str = "Spain",
        cities: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """
        Search for internship positions on LinkedIn
        
        Args:
            country: Country to search in
            cities: List of cities to filter by
            keywords: Job title/keywords to search for
            exclude_keywords: Keywords to exclude
            max_results: Maximum number of results to return
        
        Returns:
            List of job postings with metadata
        """
        if not self.driver:
            self._setup_driver()
        
        jobs = []
        search_query = "internship"
        
        if keywords:
            search_query = " ".join(keywords[:2])  # Use first 2 keywords
        
        try:
            # Build search URL
            url = self._build_search_url(
                search_query,
                country=country,
                cities=cities
            )
            logger.info(f"Searching: {url}")
            self.driver.get(url)
            
            # Wait for job listings to load
            time.sleep(3)  # Let dynamic content load
            
            # Scroll and collect job cards
            jobs = self._extract_job_listings(
                exclude_keywords=exclude_keywords,
                max_results=max_results
            )
            
            logger.info(f"✓ Found {len(jobs)} internship postings")
            
        except Exception as e:
            logger.error(f"✗ Search error: {str(e)}")
        
        return jobs
    
    def _build_search_url(
        self,
        query: str,
        country: str = "Spain",
        cities: Optional[List[str]] = None
    ) -> str:
        """Build LinkedIn job search URL with parameters"""
        # LinkedIn URL format for job search
        url = f"{self.BASE_URL}?keywords={query}"
        url += "&location=" + country.replace(" ", "%20")
        
        if cities:
            city_str = ",".join(cities).replace(" ", "%20")
            url += f"&location={city_str}"
        
        # Filter for internships and entry-level
        url += "&f_E=2&f_JT=I"  # Entry level + Internship type
        url += "&sortBy=DD"  # Sort by date descending
        
        return url
    
    def _extract_job_listings(
        self,
        exclude_keywords: Optional[List[str]] = None,
        max_results: int = 25
    ) -> List[Dict[str, Any]]:
        """Extract job listing data from LinkedIn search results"""
        jobs = []
        exclude_keywords = exclude_keywords or []
        
        try:
            # Get all job card elements
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, "[data-job-id]")
            logger.info(f"Found {len(job_cards)} job cards on page")
            
            for idx, card in enumerate(job_cards):
                if len(jobs) >= max_results:
                    break
                
                try:
                    # Click card to load details
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", card)
                    time.sleep(0.5)
                    card.click()
                    time.sleep(1)
                    
                    job_data = self._parse_job_details(card)
                    
                    if job_data and not self._contains_exclude_keywords(job_data, exclude_keywords):
                        jobs.append(job_data)
                        logger.info(f"✓ [{len(jobs)}] {job_data['position']} at {job_data['company']}")
                    
                except StaleElementReferenceException:
                    logger.warning(f"Stale element at index {idx}, skipping")
                    continue
                except Exception as e:
                    logger.warning(f"Error parsing job card {idx}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting listings: {str(e)}")
        
        return jobs
    
    def _parse_job_details(self, job_card) -> Optional[Dict[str, Any]]:
        """Parse job details from a job card element"""
        try:
            # Extract basic info from card
            job_id = job_card.get_attribute("data-job-id")
            
            # Get title
            title_elem = job_card.find_element(By.CSS_SELECTOR, "h3 a")
            position = title_elem.text.strip()
            job_url = title_elem.get_attribute("href")
            
            # Get company
            company_elem = job_card.find_element(By.CSS_SELECTOR, "h4 a, [data-test-company-name]")
            company = company_elem.text.strip()
            
            # Get location
            location_elem = job_card.find_element(By.CSS_SELECTOR, "[data-test-job-location]")
            location = location_elem.text.strip()
            
            # Parse location to get country and city
            country, city = self._parse_location(location)
            
            # Try to get description from the job detail pane
            description = self._get_job_description()
            
            # Extract salary if available
            salary = self._extract_salary(job_card, description)
            
            # Get posting date
            posted_date = self._get_posted_date(job_card)
            
            job_data = {
                "job_id": f"li_{job_id}",
                "platform": "LinkedIn",
                "company": company,
                "position": position,
                "location": city or location,
                "country": country,
                "job_url": job_url,
                "description": description,
                "salary": salary,
                "posted_date": posted_date,
                "posted_date_formatted": self._format_posted_date(posted_date),
                "employment_type": "Internship",
                "experience_level": "Entry Level",
                "scraped_at": datetime.now().isoformat()
            }
            
            return job_data
            
        except Exception as e:
            logger.warning(f"Error parsing job details: {str(e)}")
            return None
    
    def _get_job_description(self) -> str:
        """Extract job description from detail pane"""
        try:
            # Wait for description to load
            desc_elem = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".show-more-less-html__markup"))
            )
            description = desc_elem.text.strip()
            return description[:1000]  # Limit to 1000 chars
        except TimeoutException:
            logger.warning("Description not found")
            return ""
    
    def _parse_location(self, location_str: str) -> tuple[str, str]:
        """Parse location string to extract country and city"""
        parts = location_str.split(",")
        city = parts[0].strip() if len(parts) > 0 else location_str
        country = parts[-1].strip() if len(parts) > 1 else "Spain"
        
        return country, city
    
    def _extract_salary(self, job_card, description: str) -> Optional[str]:
        """Extract salary information if available"""
        try:
            # Try to find salary in job card
            salary_elem = job_card.find_element(By.CSS_SELECTOR, "[data-test-salary]")
            return salary_elem.text.strip()
        except NoSuchElementException:
            # Try to extract from description
            if "salary" in description.lower() or "€" in description:
                for line in description.split("\n"):
                    if "€" in line or "salary" in line.lower():
                        return line.strip()
            return None
    
    def _get_posted_date(self, job_card) -> Optional[str]:
        """Extract posting date"""
        try:
            date_elem = job_card.find_element(By.CSS_SELECTOR, "[data-test-job-posting-date]")
            return date_elem.get_attribute("datetime")
        except NoSuchElementException:
            return None
    
    def _format_posted_date(self, posted_date: Optional[str]) -> str:
        """Format posted date to readable string"""
        if not posted_date:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(posted_date.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except:
            return posted_date
    
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


def scrape_linkedin_internships(
    country: str = "Spain",
    cities: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    exclude_keywords: Optional[List[str]] = None,
    max_results: int = 25,
    headless: bool = True,
    db_manager=None
) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape LinkedIn internships
    
    Args:
        country: Country to search in
        cities: List of cities
        keywords: Job keywords
        exclude_keywords: Keywords to exclude
        max_results: Maximum results
        headless: Run in headless mode
        db_manager: Database manager to save results
    
    Returns:
        List of job postings
    """
    scraper = LinkedInScraper(headless=headless)
    
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
    
    finally:
        scraper.close()


if __name__ == "__main__":
    # Test the scraper
    jobs = scrape_linkedin_internships(
        country="Spain",
        cities=["Madrid", "Barcelona"],
        keywords=["Python", "AI"],
        max_results=5,
        headless=False
    )
    
    print(f"\n✓ Found {len(jobs)} internships")
    for job in jobs:
        print(f"\n  {job['position']}")
        print(f"  @ {job['company']} ({job['location']}, {job['country']})")
        print(f"  URL: {job['job_url']}")
