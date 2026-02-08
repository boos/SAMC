# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SAMC (Structured Adaptive Multi-Cycle) is an intelligent training periodization system that combines structured
programming with physiology-driven decision-making. It uses daily readiness metrics (HRV, sleep, soreness) and
vectorial load tracking (ACWR per domain) to recommend optimal training sessions.

**Core Principle:** "Structure WHAT, Adapt WHEN" - Micro-cycles define session targets, but timing is based on rolling
physiological windows, not calendar weeks.

**Current Phase:** MVP Development - Single-user, manual physio data, multi-sport (weight lifting + bicycle commuting).

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

- `app/samc/` - Core algorithms (vectorial ACWR, domain readiness, daily advisor)
- `app/sports/` - Sport plugin system (strength/, cycling/)
  - `base.py` - `SportPlugin` ABC
  - `registry.py` - `SportRegistry` singleton
- `app/schemas/stress_vector.py` - `StressVector` (0-1 clamped) and `LoadVector` (unclamped) foundation types
- `app/integrations/` - Wearable APIs (garmin/, oura/, whoop/) - Phase 2
- `app/mcp/` - Model Context Protocol integration - Phase 3

### Tech Stack

- **FastAPI** + **Uvicorn** - Web framework
- **SQLModel** - ORM (SQLAlchemy + Pydantic hybrid)
- **PostgreSQL 15 + TimescaleDB** - Database with time-series optimization
- **Alembic** - Migrations
- **JWT (python-jose) + bcrypt (passlib)** - Authentication

## Core Concepts

### 5-Domain Stress Vector

Every sport and session is characterised by a 5-dimensional stress vector:

| Domain | Description | Tolerance |
|--------|-------------|-----------|
| **Metabolico** (M) | Cardiovascular / energy system | High |
| **Neuromuscolare** (N) | CNS / motor unit recruitment | Low — structural |
| **Tendineo** (T) | Tendon / connective tissue | Low — structural |
| **Autonomico** (A) | Autonomic nervous system / recovery cost | Medium — modulator |
| **Coordinativo** (C) | Motor learning / skill coordination | High |

N and T are **structural domains** that drive micro-cycle progression.
A is a **modulator**. M and C are **high-tolerance** domains.

### Sport Plugin System

Sports are defined in code as plugins implementing `SportPlugin` ABC.
Each plugin provides: `sport_id`, `display_name`, `default_stress_profile`, `session_schema`, `compute_load()`.

**Background sports** (e.g. bicycle commuting) have `is_background=True`:
they contribute load to ACWR but do NOT occupy micro-cycle slots or affect cycle length.

Currently registered:
- `weight_lifting` — exercise-categorisation-based load (see below)
- `bicycle_commuting` (background) — duration × RPE + elevation bonus

Adding a new sport:
1. Create `app/sports/<sport>/plugin.py` implementing `SportPlugin`
2. Register in `app/sports/__init__.py`

### Exercise Categorisation System (Weight Lifting)

Each exercise is described by **5 categorical tags** with physiological rationale:

| Tag | Values | Primary domain impact |
|-----|--------|----------------------|
| **movement_type** | compound / isolation | N (CNS recruitment), A (recovery cost) |
| **eccentric_load** | high / medium / low | T (tendon stress), N (muscle damage) |
| **muscle_mass** | large / medium / small | M (metabolic demand), A (recovery cost) |
| **load_intensity** | heavy / moderate / light | N (CNS intensity), A (depletion) |
| **complexity** | high / medium / low | C (motor learning) |

A deterministic mapping function (`compute_exercise_stress_profile()`) converts tags → `StressVector`
using transparent, auditable additive contribution tables (base + per-tag contributions, clamped to [0,1]).

Key files:
- `app/sports/strength/exercise_profile.py` — Enums, ExerciseProfile model, mapping function, contribution tables
- `app/sports/strength/exercise_catalog.py` — ~22 built-in exercises with pre-assigned tags
- `app/sports/strength/plugin.py` — WeightLiftingPlugin with per-exercise load computation

**Load calculation** (no arbitrary units, no normalisation):
```
For each exercise:
    tonnage = sets × reps × weight_kg
    stress  = compute_exercise_stress_profile(5 tags)
    load    = stress.scaled_unclamped(tonnage × RPE/10)

session_load = Σ exercise_loads × intensity_modifier
```

RPE is **per exercise** (not per session). An optional `session_rpe` field is informational only.

**Custom exercises**: if an exercise is not in the catalog, the user provides the 5 tags inline:
```json
{"exercise_name": "My Press", "movement_type": "compound", "eccentric_load": "medium",
 "muscle_mass": "medium", "load_intensity": "moderate", "complexity": "low",
 "sets": 3, "reps": 10, "weight_kg": 40, "rpe": 7.0}
```

### Micro-Cycle Sizing

```
total_slots   = Σ(sessions_per_cycle) for NON-background active sports
max_recovery  = MAX(recovery_days_hint) for NON-background active sports
computed_length = total_slots + max_recovery + min_rest_days
```

User can override with `override_length_days`.

### Vectorial ACWR

The ACWR is a **monitoring and context** tool, NOT a deterministic decision mechanism.
It does not close the micro-cycle, does not predict injuries, does not automatically block training.

```
ACWR[domain] = acute_load[domain] / chronic_weekly_avg[domain]
```

- Acute = 7-day sum | Chronic = 28-day sum / 4 (weekly average)
- Encapsulated in `ACWRConfig` (ready for EWMA migration)

**Status labels** (operational categories, not absolute truths):
- `underexposed` — ACWR < 0.8
- `in_range` — 0.8 ≤ ACWR ≤ 1.3
- `spike` — 1.3 < ACWR ≤ 1.5
- `high_spike` — ACWR > 1.5
- `insufficient_history` — chronic load below minimum threshold

**Chronic load minimum thresholds** per domain prevent numerical instability
during sport introduction / return from breaks.

**Aggregation**: weighted (N=1.0, T=1.0, A=0.6, M=0.3, C=0.2) with
structural veto (N+T can override global status).

### Domain Readiness

Per-domain recovery model based on exponential fatigue decay.
Each domain has its own recovery time constant (tau):

| Domain | Tau (hours) | Literature basis |
|--------|------------|-----------------|
| M (metabolic) | 36h | Glycogen resynthesis, cardiovascular |
| C (coordination) | 36h | Motor pattern consolidation |
| A (autonomic) | 60h | ANS balance, HRV recovery |
| N (neuromuscular) | 72h | CNS fatigue, motor unit recovery |
| T (tendineo) | 120h | Collagen turnover, tendon adaptation |

```
fatigue(t) = load × exp(-t / tau)
readiness  = 1 - Σ fatigue / reference_load
```

Fatigue from multiple sessions sums (superposition).
Reference load = chronic average per session (self-calibrating).
Status labels: `recovered` (≥0.85), `partial` (0.5-0.85), `fatigued` (<0.5), `no_data`.

Key files:
- `app/samc/readiness.py` — Core computation, `ReadinessConfig`
- `app/schemas/readiness.py` — `ReadinessVector`, `ReadinessResponse`

### Daily Advisor

Three-layer architecture combining ACWR + readiness:

1. **ACWR** (guardrail) — detects load spikes / under-exposure
2. **Readiness** (decisor) — evaluates per-domain recovery state
3. **Advisor** (consequence) — combines both into a recommendation

The advisor answers:
- **Should I train today?** → `train`, `train_reduced`, `light_session`, `rest`
- **At what volume?** → factor 0.0-1.0 with label (`full`, `moderate`, `reduced`, `minimal`, `rest`)
- **Which domains can handle load?** → per-domain `can_load` boolean + guidance

Decision rules:
- ACWR `high_spike` on a domain → blocks that domain
- Readiness `fatigued` → blocks that domain
- Both structural domains (N+T) blocked → rest
- One structural blocked → minimal session
- Partial readiness → moderate volume

Key files:
- `app/samc/advisor.py` — `compute_daily_advice()`
- `app/schemas/advisor.py` — `AdvisorResponse`, `DomainGuidance`, `VolumeModifier`

### Physiological Readiness Score (future — Phase 2)

When wearable integrations arrive, a separate physiological readiness
layer will incorporate HRV, sleep, RHR, and subjective data to modulate
the domain readiness model.

## Configuration

Settings loaded via Pydantic from environment variables (see `.env.example`):

- `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_DBNAME` - DB connection
- `SECRET_KEY` - JWT signing key
- `TIMESCALEDB_ENABLED` - Enable time-series features (default: true)
- `DEBUG` - Enable debug mode and SQL logging

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register user
- `POST /api/v1/auth/login` - Login (OAuth2 form)
- `POST /api/v1/auth/token` - Login (JSON)

### Physiological Data
- `PUT /api/v1/physio/{date}` - Upsert daily physio entry
- `GET /api/v1/physio` - List with filters (date, range, pagination)
- `GET /api/v1/physio/{date}` - Get by date
- `DELETE /api/v1/physio/{date}` - Delete

### Training Sessions
- `POST /api/v1/training/sessions/{date}` - Log session
- `GET /api/v1/training/sessions/{date}` - Sessions by date
- `GET /api/v1/training/sessions` - List with date range
- `PUT /api/v1/training/sessions/id/{id}` - Update
- `DELETE /api/v1/training/sessions/id/{id}` - Delete

### Sports Configuration
- `GET /api/v1/sports/available` - List registered sport plugins
- `GET /api/v1/sports/my-sports` - User's configured sports
- `POST /api/v1/sports/my-sports` - Add sport to micro-cycle
- `PUT /api/v1/sports/my-sports/{sport_id}` - Update sport config
- `DELETE /api/v1/sports/my-sports/{sport_id}` - Remove sport
- `GET /api/v1/sports/micro-cycle` - Get micro-cycle config
- `PUT /api/v1/sports/micro-cycle` - Update micro-cycle settings

### Analytics
- `GET /api/v1/analytics/state` - Vectorial ACWR, structural status, context note
- `GET /api/v1/analytics/readiness` - Per-domain recovery readiness
- `GET /api/v1/analytics/advisor` - Daily training advice (ACWR + readiness combined)
