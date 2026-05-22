"""
Database schema and operations for tracking applications
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class ApplicationDatabase:
    """Manages SQLite database for applications and search history"""
    
    def __init__(self, db_path: Path = Path("data/applications.db")):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.conn = None
        self.init_db()
    
    def connect(self):
        """Create database connection"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def init_db(self):
        """Initialize database schema"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,
                company TEXT NOT NULL,
                position TEXT NOT NULL,
                location TEXT NOT NULL,
                country TEXT NOT NULL,
                job_url TEXT NOT NULL,
                description TEXT,
                posted_date TEXT,
                scraped_date TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                application_date TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT check_status CHECK(status IN ('pending', 'preview', 'submitted', 'rejected', 'archived'))
            )
        """)
        
        # Search filters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_filters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                country TEXT,
                cities TEXT,
                positions TEXT,
                keywords TEXT,
                exclude_keywords TEXT,
                experience_level TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Search history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filter_name TEXT,
                results_count INTEGER,
                search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (filter_name) REFERENCES search_filters(name)
            )
        """)
        
        # Application history (for bulk operations tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id INTEGER NOT NULL,
                status_before TEXT,
                status_after TEXT,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (app_id) REFERENCES applications(id)
            )
        """)
        
        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_status ON applications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_platform ON applications(platform)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_date ON applications(scraped_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_country ON applications(country)")
        
        conn.commit()
        conn.close()
    
    def add_application(self, job_data: Dict[str, Any]) -> int:
        """Add a new job application to database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO applications (
                    job_id, platform, company, position, location, country,
                    job_url, description, posted_date, scraped_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job_data.get('job_id'),
                job_data.get('platform'),
                job_data.get('company'),
                job_data.get('position'),
                job_data.get('location'),
                job_data.get('country'),
                job_data.get('job_url'),
                job_data.get('description'),
                job_data.get('posted_date'),
                datetime.now().isoformat(),
                'pending'
            ))
            conn.commit()
            app_id = cursor.lastrowid
            return app_id
        except sqlite3.IntegrityError:
            # Job already exists
            return None
        finally:
            conn.close()
    
    def get_pending_applications(self, limit: int = 10) -> List[Dict]:
        """Get pending applications for review"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM applications 
            WHERE status = 'pending'
            ORDER BY scraped_date DESC
            LIMIT ?
        """, (limit,))
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def update_application_status(self, app_id: int, new_status: str, notes: str = None) -> bool:
        """Update application status"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE applications 
                SET status = ?, 
                    application_date = CASE WHEN ? = 'submitted' THEN datetime('now') ELSE application_date END,
                    notes = COALESCE(?, notes)
                WHERE id = ?
            """, (new_status, new_status, notes, app_id))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_application_stats(self) -> Dict[str, int]:
        """Get statistics on applications"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'submitted' THEN 1 ELSE 0 END) as submitted,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM applications
        """)
        
        result = dict(cursor.fetchone())
        conn.close()
        return result
    
    def save_filter(self, filter_config: Dict[str, Any]) -> bool:
        """Save search filter configuration"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO search_filters (
                    name, country, cities, positions, keywords, 
                    exclude_keywords, experience_level, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                filter_config.get('name'),
                filter_config.get('country'),
                ','.join(filter_config.get('cities', [])),
                ','.join(filter_config.get('positions', [])),
                ','.join(filter_config.get('keywords', [])),
                ','.join(filter_config.get('exclude_keywords', [])),
                filter_config.get('experience_level')
            ))
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_filters(self, active_only: bool = True) -> List[Dict]:
        """Get saved search filters"""
        conn = self.connect()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute("SELECT * FROM search_filters WHERE is_active = 1")
        else:
            cursor.execute("SELECT * FROM search_filters")
        
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results


if __name__ == "__main__":
    # Test database
    db = ApplicationDatabase()
    print("✓ Database initialized successfully")
    
    # Add sample application
    sample_job = {
        'job_id': 'li_123456',
        'platform': 'LinkedIn',
        'company': 'TechCorp',
        'position': 'Python Developer Intern',
        'location': 'Madrid',
        'country': 'Spain',
        'job_url': 'https://linkedin.com/jobs/123456',
        'description': 'We are looking for a Python developer intern...'
    }
    
    app_id = db.add_application(sample_job)
    if app_id:
        print(f"✓ Sample application added with ID: {app_id}")
    
    # Get stats
    stats = db.get_application_stats()
    print(f"✓ Stats: {stats}")