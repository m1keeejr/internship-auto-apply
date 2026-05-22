"""
Main entry point for the internship automation tool
"""
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from cli.cli import main

if __name__ == '__main__':
    main()