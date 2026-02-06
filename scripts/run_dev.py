"""
Development server launcher.

Loads .env file and runs FastAPI with uvicorn in reload mode.

Usage:
    python scripts/run_dev.py
"""

# TODO: check if it works

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv

load_dotenv()

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("SAMC Development Server")
    print("=" * 60)
    print()
    print("Starting FastAPI application...")
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
