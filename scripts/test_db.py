"""Test database connection to Supabase."""

import sys
from pathlib import Path

# TODO: check if it works


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv

load_dotenv()

from sqlmodel import Session, create_engine, text
from app.core.config import settings

print("=" * 60)
print("Testing Supabase Connection")
print("=" * 60)
print(f"Database URL: {settings.DATABASE_URL.split('@')[1]}")  # Hide password
print()

try:
    # Create engine
    engine = create_engine(settings.DATABASE_URL, echo=True)

    # Test connection
    with Session(engine) as session:
        result = session.exec(text("SELECT version()")).first()
        print("✓ Connection successful!")
        print(f"PostgreSQL version: {result}")

        # Check if users table exists
        table_check = session.exec(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')")).first()

        if table_check:
            print("✓ 'users' table already exists")
        else:
            print("✗ 'users' table does not exist - run migration")

except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)

print("=" * 60)
