"""What would SAMC tell you TODAY (2026-02-08)?

Uses real FitNotes data to compute ACWR as of today
and produces a daily advisor output.
"""

import datetime
from collections import defaultdict

from app.samc.acwr import (
    ACWRConfig,
    _compute_domain_acwr,
    _compute_global_status,
    _compute_structural_status,
    _generate_context_note,
)
from app.schemas.acwr import ACWRVector
from app.schemas.stress_vector import DOMAIN_NAMES
from app.sports.strength.plugin import WeightLiftingPlugin

TODAY = datetime.date(2026, 2, 8)

# ─── FitNotes exercise name → SAMC catalog ID ───────────────────────
EXERCISE_MAP = {
    "Conventional Barbell Deadlift": "deadlift",
    "Barbell Zercher Squat": "zercher_squat",
    "Barbell Overhead Press": "overhead_press",
    "Barbell Flat Bench Press": "bench_press",
    "Weighted Pull-up": "pull_up",
    "Weighted Dead Bug": "weighted_dead_bug",
    "Farmer's Carry": "farmers_carry",
    "Cable Pallof Press Hold": "cable_pallof_press",
    "Plate Loaded Row Machine": "plate_loaded_row_machine",
}

CUSTOM_EXERCISES = {
    "One-Arm Dumbbell Row": {
        "movement_type": "compound",
        "eccentric_load": "medium",
        "muscle_mass": "medium",
        "load_intensity": "moderate",
        "complexity": "low",
    },
    "Chin-up": {
        "movement_type": "compound",
        "eccentric_load": "medium",
        "muscle_mass": "medium",
        "load_intensity": "moderate",
        "complexity": "medium",
    },
}

DEFAULT_RPE = 7.0

RAW_DATA = [
    ("2025-11-13", "Conventional Barbell Deadlift", 40, 10),
    ("2025-11-13", "Conventional Barbell Deadlift", 60, 5),
    ("2025-11-13", "Conventional Barbell Deadlift", 80, 3),
    ("2025-11-13", "Conventional Barbell Deadlift", 90, 2),
    ("2025-11-13", "Conventional Barbell Deadlift", 90, 2),
    ("2025-11-13", "Conventional Barbell Deadlift", 90, 2),
    ("2025-11-13", "One-Arm Dumbbell Row", 5, 10),
    ("2025-11-13", "Farmer's Carry", 60, 0),
    ("2025-11-13", "Farmer's Carry", 60, 0),
    ("2025-11-13", "Farmer's Carry", 60, 0),
    ("2025-11-13", "Cable Pallof Press Hold", 14, 0),
    ("2025-11-13", "Cable Pallof Press Hold", 16, 0),
    ("2025-11-13", "Cable Pallof Press Hold", 18, 0),
    ("2025-11-13", "One-Arm Dumbbell Row", 5, 10),
    ("2025-11-13", "One-Arm Dumbbell Row", 7.5, 10),
    ("2025-11-13", "One-Arm Dumbbell Row", 7.5, 10),
    ("2025-11-23", "Weighted Pull-up", 0, 5),
    ("2025-11-23", "Weighted Pull-up", 2.5, 4),
    ("2025-11-23", "Weighted Pull-up", 5, 4),
    ("2025-11-23", "Barbell Zercher Squat", 20, 6),
    ("2025-11-23", "Barbell Zercher Squat", 40, 5),
    ("2025-11-23", "Barbell Zercher Squat", 50, 4),
    ("2025-11-23", "Barbell Zercher Squat", 55, 3),
    ("2025-11-23", "Barbell Overhead Press", 20, 8),
    ("2025-11-23", "Barbell Overhead Press", 30, 5),
    ("2025-11-23", "Barbell Overhead Press", 35, 3),
    ("2025-11-23", "Barbell Overhead Press", 37.5, 2),
    ("2025-11-23", "Weighted Dead Bug", 5, 4),
    ("2025-11-23", "Weighted Dead Bug", 5, 4),
    ("2025-11-23", "Weighted Dead Bug", 5, 4),
    ("2025-11-26", "Weighted Pull-up", 0, 6),
    ("2025-11-26", "Weighted Pull-up", 2.5, 4),
    ("2025-11-26", "Weighted Pull-up", 5, 4),
    ("2025-11-26", "Weighted Pull-up", 7.5, 3),
    ("2025-11-26", "Barbell Zercher Squat", 20, 7),
    ("2025-11-26", "Barbell Zercher Squat", 40, 5),
    ("2025-11-26", "Barbell Zercher Squat", 50, 4),
    ("2025-11-26", "Barbell Zercher Squat", 55, 4),
    ("2025-11-26", "Barbell Zercher Squat", 60, 3),
    ("2025-11-26", "Barbell Overhead Press", 20, 7),
    ("2025-11-26", "Barbell Overhead Press", 30, 5),
    ("2025-11-26", "Barbell Overhead Press", 35, 3),
    ("2025-11-26", "Barbell Overhead Press", 37.5, 3),
    ("2025-11-26", "Barbell Flat Bench Press", 20, 10),
    ("2025-11-26", "Barbell Flat Bench Press", 40, 5),
    ("2025-11-26", "Barbell Flat Bench Press", 40, 6),
    ("2025-11-26", "Weighted Dead Bug", 5, 5),
    ("2025-11-26", "Weighted Dead Bug", 5, 5),
    ("2025-11-26", "Weighted Dead Bug", 5, 5),
    ("2025-12-05", "Conventional Barbell Deadlift", 40, 8),
    ("2025-12-05", "Conventional Barbell Deadlift", 60, 5),
    ("2025-12-05", "Conventional Barbell Deadlift", 75, 3),
    ("2025-12-05", "Conventional Barbell Deadlift", 75, 3),
    ("2025-12-05", "Conventional Barbell Deadlift", 75, 3),
    ("2025-12-05", "One-Arm Dumbbell Row", 8, 10),
    ("2025-12-05", "One-Arm Dumbbell Row", 8, 10),
    ("2025-12-05", "One-Arm Dumbbell Row", 12.5, 10),
    ("2025-12-05", "Farmer's Carry", 60, 0),
    ("2025-12-05", "Farmer's Carry", 60, 0),
    ("2025-12-05", "Farmer's Carry", 60, 0),
    ("2025-12-05", "Cable Pallof Press Hold", 14, 0),
    ("2025-12-05", "Cable Pallof Press Hold", 14, 0),
    ("2025-12-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2025-12-05", "One-Arm Dumbbell Row", 12.5, 10),
    ("2025-12-05", "One-Arm Dumbbell Row", 12.5, 8),
    ("2025-12-05", "One-Arm Dumbbell Row", 12.5, 8),
    ("2025-12-05", "One-Arm Dumbbell Row", 15, 6),
    ("2025-12-05", "One-Arm Dumbbell Row", 15, 6),
    ("2025-12-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2025-12-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2025-12-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2025-12-07", "Weighted Pull-up", 0, 5),
    ("2025-12-07", "Weighted Pull-up", 2.5, 4),
    ("2025-12-07", "Weighted Pull-up", 5, 4),
    ("2025-12-07", "Barbell Zercher Squat", 20, 6),
    ("2025-12-07", "Barbell Zercher Squat", 40, 6),
    ("2025-12-07", "Barbell Zercher Squat", 50, 4),
    ("2025-12-07", "Barbell Zercher Squat", 55, 4),
    ("2025-12-07", "Barbell Overhead Press", 20, 8),
    ("2025-12-07", "Barbell Overhead Press", 30, 5),
    ("2025-12-07", "Barbell Overhead Press", 35, 3),
    ("2025-12-07", "Barbell Overhead Press", 37.5, 2),
    ("2025-12-07", "Weighted Dead Bug", 5, 5),
    ("2025-12-07", "Weighted Dead Bug", 5, 5),
    ("2025-12-07", "Weighted Dead Bug", 5, 5),
    ("2025-12-07", "Weighted Pull-up", 5, 3),
    ("2025-12-07", "Barbell Zercher Squat", 60, 3),
    ("2025-12-07", "Barbell Overhead Press", 35, 3),
    ("2025-12-21", "Conventional Barbell Deadlift", 40, 10),
    ("2025-12-21", "Conventional Barbell Deadlift", 60, 5),
    ("2025-12-21", "Conventional Barbell Deadlift", 80, 3),
    ("2025-12-21", "Conventional Barbell Deadlift", 95, 2),
    ("2025-12-21", "One-Arm Dumbbell Row", 12.5, 8),
    ("2025-12-21", "One-Arm Dumbbell Row", 15, 6),
    ("2025-12-21", "Cable Pallof Press Hold", 16, 0),
    ("2025-12-21", "Cable Pallof Press Hold", 18, 0),
    ("2025-12-21", "Cable Pallof Press Hold", 20, 0),
    ("2025-12-21", "Conventional Barbell Deadlift", 95, 2),
    ("2025-12-21", "One-Arm Dumbbell Row", 15, 6),
    ("2026-01-05", "Conventional Barbell Deadlift", 40, 10),
    ("2026-01-05", "One-Arm Dumbbell Row", 8, 10),
    ("2026-01-05", "Farmer's Carry", 60, 0),
    ("2026-01-05", "Cable Pallof Press Hold", 14, 0),
    ("2026-01-05", "Conventional Barbell Deadlift", 60, 5),
    ("2026-01-05", "Conventional Barbell Deadlift", 75, 3),
    ("2026-01-05", "Conventional Barbell Deadlift", 75, 3),
    ("2026-01-05", "Conventional Barbell Deadlift", 75, 3),
    ("2026-01-05", "One-Arm Dumbbell Row", 8, 10),
    ("2026-01-05", "One-Arm Dumbbell Row", 12.5, 10),
    ("2026-01-05", "One-Arm Dumbbell Row", 12.5, 10),
    ("2026-01-05", "One-Arm Dumbbell Row", 12.5, 8),
    ("2026-01-05", "One-Arm Dumbbell Row", 12.5, 8),
    ("2026-01-05", "One-Arm Dumbbell Row", 15, 6),
    ("2026-01-05", "One-Arm Dumbbell Row", 15, 6),
    ("2026-01-05", "Farmer's Carry", 60, 0),
    ("2026-01-05", "Farmer's Carry", 60, 0),
    ("2026-01-05", "Cable Pallof Press Hold", 14, 0),
    ("2026-01-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2026-01-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2026-01-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2026-01-05", "Cable Pallof Press Hold", 16.3, 0),
    ("2026-01-10", "Weighted Pull-up", 0, 5),
    ("2026-01-10", "Weighted Pull-up", 2.5, 5),
    ("2026-01-10", "Weighted Pull-up", 5, 4),
    ("2026-01-10", "Barbell Zercher Squat", 20, 6),
    ("2026-01-10", "Barbell Zercher Squat", 40, 6),
    ("2026-01-10", "Barbell Zercher Squat", 50, 5),
    ("2026-01-10", "Barbell Zercher Squat", 55, 5),
    ("2026-01-10", "Barbell Overhead Press", 20, 8),
    ("2026-01-10", "Barbell Overhead Press", 30, 5),
    ("2026-01-10", "Barbell Overhead Press", 32.5, 4),
    ("2026-01-10", "Barbell Overhead Press", 35, 1),
    ("2026-01-10", "Barbell Flat Bench Press", 20, 10),
    ("2026-01-10", "Barbell Flat Bench Press", 40, 5),
    ("2026-01-10", "Barbell Flat Bench Press", 45, 5),
    ("2026-01-10", "Weighted Dead Bug", 5, 5),
    ("2026-01-10", "Weighted Dead Bug", 5, 5),
    ("2026-01-10", "Weighted Dead Bug", 5, 5),
    ("2026-01-10", "Barbell Flat Bench Press", 50, 4),
    ("2026-01-10", "Barbell Flat Bench Press", 52.5, 3),
    ("2026-01-10", "Weighted Pull-up", 5, 3),
    ("2026-01-16", "Chin-up", 0, 7),
    ("2026-01-16", "Chin-up", 0, 5),
    ("2026-01-16", "Chin-up", 0, 4),
    ("2026-01-16", "Conventional Barbell Deadlift", 40, 8),
    ("2026-01-16", "Conventional Barbell Deadlift", 60, 5),
    ("2026-01-16", "Conventional Barbell Deadlift", 75, 3),
    ("2026-01-16", "Conventional Barbell Deadlift", 80, 3),
    ("2026-01-16", "Conventional Barbell Deadlift", 85, 3),
    ("2026-01-16", "Plate Loaded Row Machine", 20, 10),
    ("2026-01-16", "Plate Loaded Row Machine", 40, 10),
    ("2026-01-16", "Plate Loaded Row Machine", 50, 6),
    ("2026-01-16", "Plate Loaded Row Machine", 50, 5),
    ("2026-01-16", "Cable Pallof Press Hold", 16, 0),
    ("2026-01-16", "Cable Pallof Press Hold", 16, 0),
    ("2026-01-16", "Cable Pallof Press Hold", 18, 0),
    ("2026-01-16", "Cable Pallof Press Hold", 18, 0),
    ("2026-01-16", "Cable Pallof Press Hold", 20, 0),
    ("2026-01-16", "Cable Pallof Press Hold", 20, 0),
    ("2026-01-26", "Barbell Zercher Squat", 20, 8),
    ("2026-01-26", "Barbell Zercher Squat", 30, 5),
    ("2026-01-26", "Barbell Zercher Squat", 50, 5),
    ("2026-01-26", "Barbell Zercher Squat", 50, 5),
    ("2026-01-26", "Weighted Pull-up", 0, 5),
    ("2026-01-26", "Weighted Pull-up", 2.5, 3),
    ("2026-01-26", "Weighted Pull-up", 5, 4),
    ("2026-01-26", "Weighted Pull-up", 5, 3),
    ("2026-01-26", "Barbell Overhead Press", 20, 8),
    ("2026-01-26", "Barbell Overhead Press", 25, 5),
    ("2026-01-26", "Barbell Overhead Press", 30, 5),
    ("2026-01-26", "Barbell Overhead Press", 30, 4),
    ("2026-01-26", "Barbell Flat Bench Press", 20, 8),
    ("2026-01-26", "Barbell Flat Bench Press", 32.5, 5),
    ("2026-01-26", "Barbell Flat Bench Press", 42.5, 5),
    ("2026-01-26", "Barbell Flat Bench Press", 42.5, 5),
    ("2026-01-26", "Weighted Dead Bug", 4, 12),
    ("2026-01-26", "Weighted Dead Bug", 4, 12),
    ("2026-01-31", "Conventional Barbell Deadlift", 50, 5),
    ("2026-01-31", "Conventional Barbell Deadlift", 70, 3),
    ("2026-01-31", "Conventional Barbell Deadlift", 85, 2),
    ("2026-01-31", "Conventional Barbell Deadlift", 85, 2),
    ("2026-01-31", "Conventional Barbell Deadlift", 85, 2),
    ("2026-01-31", "Plate Loaded Row Machine", 35, 8),
    ("2026-01-31", "Plate Loaded Row Machine", 50, 6),
    ("2026-01-31", "Plate Loaded Row Machine", 60, 5),
    ("2026-01-31", "Plate Loaded Row Machine", 70, 5),
    ("2026-01-31", "Plate Loaded Row Machine", 60, 7),
    ("2026-01-31", "Chin-up", 0, 5),
    ("2026-01-31", "Chin-up", 2.5, 4),
    ("2026-01-31", "Chin-up", 2.5, 4),
    ("2026-01-31", "Chin-up", 0, 5),
    ("2026-01-31", "Farmer's Carry", 65, 0),
    ("2026-01-31", "Farmer's Carry", 65, 0),
    ("2026-01-31", "Farmer's Carry", 65, 0),
    ("2026-01-31", "Cable Pallof Press Hold", 20.3, 0),
    ("2026-01-31", "Cable Pallof Press Hold", 20.3, 0),
    ("2026-01-31", "Cable Pallof Press Hold", 16.3, 0),
    ("2026-01-31", "Cable Pallof Press Hold", 16.3, 0),
]


def compute_daily_loads(raw_data):
    """Convert raw set data into daily LoadVectors."""
    plugin = WeightLiftingPlugin()
    sessions_by_date = defaultdict(list)
    for date, exercise, weight_kg, reps in raw_data:
        sessions_by_date[date].append((exercise, weight_kg, reps))

    daily_loads = {}
    for date in sorted(sessions_by_date.keys()):
        exercises = []
        for exercise_name, weight_kg, reps in sessions_by_date[date]:
            effective_reps = max(reps, 1)
            if exercise_name in EXERCISE_MAP:
                exercises.append({
                    "exercise_id": EXERCISE_MAP[exercise_name],
                    "sets": 1, "reps": effective_reps,
                    "weight_kg": weight_kg, "rpe": DEFAULT_RPE,
                })
            elif exercise_name in CUSTOM_EXERCISES:
                exercises.append({
                    "exercise_name": exercise_name,
                    **CUSTOM_EXERCISES[exercise_name],
                    "sets": 1, "reps": effective_reps,
                    "weight_kg": weight_kg, "rpe": DEFAULT_RPE,
                })
        daily_loads[date] = plugin.compute_load(
            {"exercises": exercises}, intensity_modifier=1.0
        )
    return daily_loads


def compute_acwr_at(daily_loads, check_date, cfg):
    """Compute ACWR state at a specific date."""
    acute_start = check_date - datetime.timedelta(days=cfg.acute_days - 1)
    chronic_start = check_date - datetime.timedelta(days=cfg.chronic_days - 1)

    acute_sums = {d: 0.0 for d in DOMAIN_NAMES}
    chronic_sums = {d: 0.0 for d in DOMAIN_NAMES}

    for date_str, load in daily_loads.items():
        d = datetime.date.fromisoformat(date_str)
        if acute_start <= d <= check_date:
            for domain in DOMAIN_NAMES:
                acute_sums[domain] += getattr(load, domain)
        if chronic_start <= d <= check_date:
            for domain in DOMAIN_NAMES:
                chronic_sums[domain] += getattr(load, domain)

    domain_results = {}
    for domain in DOMAIN_NAMES:
        domain_results[domain] = _compute_domain_acwr(
            domain=domain,
            acute_sum=acute_sums[domain],
            chronic_sum=chronic_sums[domain],
            chronic_weeks=cfg.chronic_weeks,
            min_threshold=cfg.min_chronic_thresholds[domain],
        )

    acwr_vector = ACWRVector(**domain_results)
    structural = _compute_structural_status(
        domain_results["neuromuscular"], domain_results["tendineo"]
    )
    global_status = _compute_global_status(
        acwr_vector, structural, cfg.domain_weights
    )
    context = _generate_context_note(acwr_vector, structural, global_status)

    return {
        "acwr_vector": acwr_vector,
        "domain_results": domain_results,
        "structural": structural,
        "global_status": global_status,
        "context": context,
        "acute_sums": acute_sums,
        "chronic_sums": chronic_sums,
    }


def main():
    daily_loads = compute_daily_loads(RAW_DATA)
    cfg = ACWRConfig()

    # ── Compute state as of TODAY ───────────────────────────────────
    state = compute_acwr_at(daily_loads, TODAY, cfg)
    all_dates = sorted(daily_loads.keys())

    last_training = datetime.date.fromisoformat(all_dates[-1])
    days_since = (TODAY - last_training).days

    # ── Determine session types from history ────────────────────────
    # Session A = "Deadlift day" (deadlift + rows + carry + pallof)
    # Session B = "Squat/Press day" (squat + press + bench + pull-ups + dead bug)

    # Count sessions in chronic window
    chronic_start = TODAY - datetime.timedelta(days=cfg.chronic_days - 1)
    sessions_in_window = sum(
        1 for d in all_dates
        if datetime.date.fromisoformat(d) >= chronic_start
    )

    # ── PRINT DAILY ADVISOR ─────────────────────────────────────────
    print()
    print("=" * 65)
    print(f"  SAMC Daily Advisor — {TODAY.strftime('%A %d %B %Y')}")
    print("=" * 65)
    print()

    # Last training
    print(f"  Ultimo allenamento:  {last_training} ({days_since} giorni fa)")
    print(f"  Sessioni ultimi 28g: {sessions_in_window}")
    print()

    # ACWR per domain
    print("  ACWR per dominio:")
    print(f"  {'Dominio':<16} {'ACWR':>7} {'Status':<20} {'Acute':>8} {'Chronic':>8}")
    print("  " + "-" * 63)
    for domain in DOMAIN_NAMES:
        dacwr = state["domain_results"][domain]
        val = f"{dacwr.value:.2f}" if dacwr.value is not None else "--"
        print(
            f"  {domain:<16} {val:>7} {dacwr.status:<20} "
            f"{dacwr.acute_load:>8.0f} {dacwr.chronic_load:>8.0f}"
        )

    print()
    print(f"  Stato strutturale: {state['structural']}")
    print(f"  Stato globale:     {state['global_status']}")
    print()

    # ── DECISION LOGIC ──────────────────────────────────────────────
    print("  " + "-" * 63)
    print("  RACCOMANDAZIONE:")
    print("  " + "-" * 63)

    # Determine what the last session was
    last_session_date = all_dates[-1]
    last_exercises = set()
    for date, ex, _, _ in RAW_DATA:
        if date == last_session_date:
            last_exercises.add(ex)

    was_deadlift_day = "Conventional Barbell Deadlift" in last_exercises
    next_session = "Squat/Press day" if was_deadlift_day else "Deadlift day"

    gs = state["global_status"]
    ss = state["structural"]

    if gs == "insufficient_data":
        # Not enough data — just train
        print()
        print(f"  >>> ALLENATI OGGI: {next_session}")
        print()
        print("  Dati insufficienti per un monitoraggio ACWR completo.")
        print("  Procedi con volume normale per accumulare dati.")
        print()
        if next_session == "Deadlift day":
            print("  Sessione suggerita:")
            print("    - Deadlift: ramp up fino a working sets")
            print("    - Row Machine o DB Row: 3-5 x 6-10")
            print("    - Farmer's Carry: 3 x walk")
            print("    - Cable Pallof Press: 3-4 x hold")
        else:
            print("  Sessione suggerita:")
            print("    - Zercher Squat: ramp up fino a working sets")
            print("    - Overhead Press: 3-4 x 3-5")
            print("    - Bench Press: 3-4 x 5-8")
            print("    - Pull-ups/Chin-ups: 3-4 x 3-5")
            print("    - Dead Bug: 2-3 x 5")

    elif gs == "underexposed":
        # Acute load = 0, no training this week
        print()
        print(f"  >>> ALLENATI OGGI: {next_session}")
        print()
        print(f"  Non ti alleni da {days_since} giorni.")
        print("  Tutti i domini sono sotto-esposti (acute = 0).")

        if days_since <= 5:
            print("  Volume: NORMALE — ripresa regolare.")
        elif days_since <= 10:
            print("  Volume: MODERATO — riduci il 10-20% del tonnage")
            print("  per rientrare gradualmente.")
        else:
            print("  Volume: RIDOTTO — dopo una pausa lunga, riduci")
            print("  il 20-30% del tonnage per evitare DOMS eccessivo.")
            print("  I pesi pesanti li riprendi nella prossima sessione.")

        print()
        if next_session == "Deadlift day":
            print("  Sessione suggerita:")
            print("    - Deadlift: warm-up + 3x3 al 80-85% (non max)")
            print("    - Row Machine o DB Row: 3-4 x 8-10")
            print("    - Farmer's Carry: 3 x walk")
            print("    - Cable Pallof Press: 3 x hold")
        else:
            print("  Sessione suggerita:")
            print("    - Zercher Squat: warm-up + 3-4 x 4-5 al 80%")
            print("    - Overhead Press: 3 x 5 moderato")
            print("    - Bench Press: 3 x 5-6 moderato")
            print("    - Pull-ups: 3 x 4-5 (no added weight)")
            print("    - Dead Bug: 2 x 8-10")

    elif gs in ("in_range",):
        # Sweet spot — train normally
        print()
        print(f"  >>> ALLENATI OGGI: {next_session}")
        print()
        print("  Carico stabile, tutti i domini in range.")
        print("  Volume: NORMALE — puoi spingere se ti senti bene.")

    elif gs == "spike":
        # Moderate spike — train but reduce volume
        print()
        if ss == "structural_alert":
            print("  >>> RIPOSO o SESSIONE LEGGERA")
            print()
            print("  I domini strutturali (N/T) sono in alert.")
            print("  Meglio un giorno di riposo o una sessione leggera")
            print("  (solo mobility e core).")
        else:
            print(f"  >>> ALLENATI OGGI: {next_session} (volume ridotto)")
            print()
            print("  ACWR in zona spike — riduci il volume del 20-30%.")
            print("  Mantieni i working weights ma con meno serie.")

    elif gs == "high_spike":
        # High spike — rest or very light
        print()
        if days_since <= 2:
            print("  >>> RIPOSO")
            print()
            print("  Hai appena fatto una sessione intensa.")
            print("  ACWR in high spike — il corpo sta assorbendo il carico.")
            print("  Riprendi tra 2-3 giorni.")
        else:
            print(f"  >>> ALLENATI OGGI: {next_session} (volume ridotto)")
            print()
            print("  ACWR elevato ma sono passati giorni dalla sessione.")
            print("  Il high spike riflette la bassa frequenza, non il")
            print("  sovraccarico reale. Allenati con volume moderato.")

    # ── Frequency note ──────────────────────────────────────────────
    print()
    print("  " + "-" * 63)
    print("  NOTA SULLA FREQUENZA:")
    weeks_in_period = max(
        1, (TODAY - datetime.date.fromisoformat(all_dates[0])).days / 7
    )
    freq = len(all_dates) / weeks_in_period
    print(f"  Frequenza attuale: {freq:.1f} sessioni/settimana")
    if freq < 1.5:
        print("  La frequenza e' bassa. L'ACWR oscilla tra 'underexposed'")
        print("  e 'spike' perche' il chronic non si stabilizza.")
        print("  Obiettivo: almeno 2 sessioni/settimana per un ACWR")
        print("  significativo.")
    elif freq < 2.5:
        print("  Frequenza accettabile per il monitoring ACWR.")
    else:
        print("  Frequenza buona per un monitoring ACWR stabile.")


if __name__ == "__main__":
    main()
