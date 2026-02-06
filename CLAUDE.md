# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAMC (Structured Adaptive Multi-Cycle) is an intelligent training periodization system that combines structured
programming with physiology-driven decision-making. It uses daily readiness metrics (HRV, sleep, soreness) and load
tracking (ACWR) to recommend optimal training sessions.

**Core Principle:** "Structure WHAT, Adapt WHEN" - Micro-cycles define session targets, but timing is based on rolling
physiological windows, not calendar weeks.

**Current Phase:** MVP Development (Week 1-8) - Single-user, manual physio data, strength training focus.

## Build and Development Commands

```bash
# Setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env

# Database
docker-compose up -d postgres
python scripts/init_db.py

# Run dev server (http://localhost:8000, docs at /docs)
python scripts/run_dev.py

# Migrations
alembic revision --autogenerate -m "message"
alembic upgrade head

# Testing
pytest                              # All tests
pytest --cov=app                    # With coverage
pytest tests/unit/test_file.py -v   # Single file
pytest tests/integration/ -v        # Integration only

# Code quality
black app/ tests/
ruff check app/ tests/
mypy app/
```

## Architecture

### Layer Structure

```
API (app/api/v1/) → Services (app/services/) → Repositories (app/db/repositories/) → Database
```

### Key Directories

- `app/samc/` - Core algorithms (readiness calculation, ACWR, decision logic)
- `app/sports/` - Sport plugin system (strength/, climbing/, running/)
- `app/integrations/` - Wearable APIs (garmin/, oura/, whoop/) - Phase 2
- `app/mcp/` - Model Context Protocol integration - Phase 3

### Tech Stack

- **FastAPI** + **Uvicorn** - Web framework
- **SQLModel** - ORM (SQLAlchemy + Pydantic hybrid)
- **PostgreSQL 15 + TimescaleDB** - Database with time-series optimization
- **Alembic** - Migrations
- **JWT (python-jose) + bcrypt (passlib)** - Authentication

## Core Algorithms

### Readiness Score

```
Readiness = HRV×0.4 + Sleep×0.3 + RHR×0.2 + Subjective×0.1
```

Components normalized to 0-10 scale based on 7-day baselines.

### ACWR (Acute:Chronic Workload Ratio)

```
ACWR = Acute (7d) / Chronic (28d)
```

- Sweet Spot: 0.8-1.3 | Caution: 1.3-1.5 | Danger: >1.5

### Decision Tree

```
ACWR > 1.5        → REST (injury risk override)
Readiness < 6     → REST
Readiness 6-7.5   → REDUCED (-20% volume OR -10% intensity)
Readiness > 7.5   → FULL session
```

### Strength Load (Arbitrary Units)

```
AU = Σ(sets × reps × kg × RPE/10)
```

## Configuration

Settings loaded via Pydantic from environment variables (see `.env.example`):

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key
- `TIMESCALEDB_ENABLED` - Enable time-series features (default: true)
- `DEBUG` - Enable debug mode and SQL logging

## API Endpoints (Planned for MVP)

- `POST /api/v1/auth/register`, `/login` - Authentication
- `POST/GET /api/v1/physio` - Daily physiology data
- `POST/GET /api/v1/training/sessions` - Training session logging
- `GET /api/v1/analytics/state` - Current readiness and ACWR
- `GET /api/v1/decision/next-session` - Session recommendation
