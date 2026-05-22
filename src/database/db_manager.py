"""
Database schema and operations for tracking applications
"""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import json


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
        
        # Applications table (with extracted metadata)
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
                
                -- Extracted metadata for filtering
                languages TEXT,
                required_languages TEXT,
                hours_per_week INTEGER,
                hours_type TEXT,
                remote_type TEXT,
                employment_type TEXT,
                experience_level TEXT,
                is_paid BOOLEAN,
                duration_months INTEGER,
                skills_required TEXT,
                salary TEXT,
                
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
                required_languages TEXT,
                optional_languages TEXT,
                min_hours INTEGER,
                max_hours INTEGER,
                remote_type TEXT,
                experience_level TEXT,
                paid_only BOOLEAN,
                match_threshold INTEGER DEFAULT 50,
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
        
        # Application history (audit trail)
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_languages ON applications(languages)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_app_remote ON applications(remote_type)")
        
        conn.commit()
        conn.close()
    
    def add_application(self, job_data: Dict[str, Any], extracted_data: Optional[Dict[str, Any]] = None) -> int:
        """Add a new job application to database"""
        conn = self.connect()
        cursor = conn.cursor()
        
        try:
            # Prepare extracted data
            extracted_data = extracted_data or {}
            
            cursor.execute("""
                INSERT INTO applications (
                    job_id, platform, company, position, location, country,
                    job_url, description, posted_date, scraped_date, status,
                    languages, required_languages, hours_per_week, hours_type,
                    remote_type, employment_type, experience_level, is_paid,
                    duration_months, skills_required, salary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                'pending',
                extracted_data.get('languages', ''),
                extracted_data.get('required_languages', ''),
                extracted_data.get('hours_per_week'),
                extracted_data.get('hours_type'),
                extracted_data.get('remote_type'),
                extracted_data.get('employment_type'),
                extracted_data.get('experience_level'),
                extracted_data.get('is_paid', False),
                extracted_data.get('duration_months'),
                extracted_data.get('skills_required', ''),
                job_data.get('salary')
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
            # Get old status first
            cursor.execute("SELECT status FROM applications WHERE id = ?", (app_id,))
            row = cursor.fetchone()
            old_status = row[0] if row else None
            
            # Update status
            cursor.execute("""
                UPDATE applications 
                SET status = ?, 
                    application_date = CASE WHEN ? = 'submitted' THEN datetime('now') ELSE application_date END,
                    notes = COALESCE(?, notes)
                WHERE id = ?
            """, (new_status, new_status, notes, app_id))
            
            # Add to history
            if old_status and old_status != new_status:
                cursor.execute("""
                    INSERT INTO application_history (app_id, status_before, status_after, action, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (app_id, old_status, new_status, 'status_change', notes))
            
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
                    exclude_keywords, required_languages, optional_languages,
                    min_hours, max_hours, remote_type, experience_level,
                    paid_only, match_threshold, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                filter_config.get('name'),
                filter_config.get('country'),
                ','.join(filter_config.get('cities', [])),
                ','.join(filter_config.get('positions', [])),
                ','.join(filter_config.get('keywords', [])),
                ','.join(filter_config.get('exclude_keywords', [])),
                ','.join(filter_config.get('required_languages', [])),
                ','.join(filter_config.get('optional_languages', [])),
                filter_config.get('min_hours'),
                filter_config.get('max_hours'),
                filter_config.get('remote_type'),
                filter_config.get('experience_level'),
                filter_config.get('paid_only', False),
                filter_config.get('match_threshold', 50)
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
    
    def search_applications(self, **filters) -> List[Dict]:
        """Advanced search on applications with filtering"""
        conn = self.connect()
        cursor = conn.cursor()
        
        query = "SELECT * FROM applications WHERE 1=1"
        params = []
        
        # Add dynamic filters
        if 'status' in filters:
            query += " AND status = ?"
            params.append(filters['status'])
        
        if 'platform' in filters:
            query += " AND platform = ?"
            params.append(filters['platform'])
        
        if 'country' in filters:
            query += " AND country = ?"
            params.append(filters['country'])
        
        if 'languages' in filters:
            # JSON-like search in languages field
            lang = filters['languages']
            query += " AND languages LIKE ?"
            params.append(f"%{lang}%")
        
        if 'remote_type' in filters:
            query += " AND remote_type = ?"
            params.append(filters['remote_type'])
        
        query += " ORDER BY scraped_date DESC LIMIT 50"
        
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return results


if __name__ == "__main__":
    # Test database
    db = ApplicationDatabase()
    print("✓ Database initialized successfully")
