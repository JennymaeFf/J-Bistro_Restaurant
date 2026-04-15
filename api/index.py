import sys
from pathlib import Path

# Add parent directory to path to import app.py
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from app import app

# Export the app for Vercel
__all__ = ['app']
