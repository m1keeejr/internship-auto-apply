# Internship Application Automation Tool

Automate internship job searches and applications across European job boards.

## Features
- Multi-platform job board integration (LinkedIn, Indeed, Glassdoor, etc.)
- Custom filtering by location, role, keywords
- Auto-fill applications with your CV data
- Review-before-submit workflow for safety
- Application tracking and history
- CLI-based interface

## Quick Start

### Installation
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
```bash
python src/main.py init
```

### Search for Internships
```bash
python src/main.py search --country Spain --city Madrid --role "Software Engineer" --keywords Python,AI
```

### View & Submit Applications
```bash
python src/main.py status
python src/main.py submit <application_id>
```

## Project Structure
```
internship-auto-apply/
├── src/
│   ├── config/          # Configuration loaders
│   ├── scrapers/        # Job board scrapers
│   ├── filters/         # Filtering logic
│   ├── profile/         # CV/profile management
│   ├── forms/           # Form automation
│   ├── database/        # Database schema & queries
│   ├── cli/             # CLI commands
│   └── main.py          # Entry point
├── config/
│   ├── cv_template.json # Your CV data (create with 'init')
│   ├── filters.json     # Search filters config
│   └── credentials.json # API keys (gitignored)
├── data/
│   ├── applications.db  # SQLite database
│   └── logs/            # Application logs
└── requirements.txt
```

## Development
Run tests:
```bash
pytest tests/
```

## License
MIT