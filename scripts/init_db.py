"""
Database initialization script.

Run this script to create database tables and setup TimescaleDB.

Usage:
    python scripts/init_db.py
"""

# TODO: check if it works
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.init_db import init_db

if __name__ == "__main__":
    print("=" * 50)
    print("SAMC Database Initialization")
    print("=" * 50)
    print()

    try:
        init_db()
        print()
        print("=" * 50)
        print("SUCCESS: Database initialized!")
        print("=" * 50)
        sys.exit(0)

    except Exception as e:
        print()
        print("=" * 50)
        print(f"ERROR: Database initialization failed!")
        print(f"Details: {e}")
        print("=" * 50)
        sys.exit(1)
