"""Simulate ACWR from real FitNotes training data (last 3 months)."""

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

# Exercises NOT in catalog — provide custom tags
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

# FitNotes has no RPE — use 7.0 as a reasonable default
DEFAULT_RPE = 7.0

# ─── Raw data from FitNotes (reps=0 for isometrics → treated as 1) ──
RAW_DATA = [
    # Nov 13 - Deadlift day
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
    # Nov 23 - Squat/Press day
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
    # Nov 26
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
    # Dec 5 - Deadlift day
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
    # Dec 7
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
    # Dec 21 - Deadlift day
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
    # Jan 5 - Deadlift day
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
    # Jan 10 - Squat/Press day
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
    # Jan 16 - Deadlift day
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
    # Jan 26 - Squat/Press day
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
    # Jan 31 - Deadlift day
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


def main():
    plugin = WeightLiftingPlugin()
    cfg = ACWRConfig()

    # ── Group sets by date ──────────────────────────────────────────
    sessions_by_date: dict[str, list] = defaultdict(list)
    for date, exercise, weight_kg, reps in RAW_DATA:
        sessions_by_date[date].append((exercise, weight_kg, reps))

    # ── Compute daily LoadVectors ───────────────────────────────────
    daily_loads: dict[str, object] = {}

    print()
    print("=" * 90)
    print(
        f"{'Date':<12} {'Sets':>5} {'M':>8} {'N':>8} {'T':>8} "
        f"{'A':>8} {'C':>8}"
    )
    print("=" * 90)

    for date in sorted(sessions_by_date.keys()):
        sets_data = sessions_by_date[date]
        exercises = []

        for exercise_name, weight_kg, reps in sets_data:
            effective_reps = max(reps, 1)  # isometrics: reps=0 → 1

            if exercise_name in EXERCISE_MAP:
                exercises.append(
                    {
                        "exercise_id": EXERCISE_MAP[exercise_name],
                        "sets": 1,
                        "reps": effective_reps,
                        "weight_kg": weight_kg,
                        "rpe": DEFAULT_RPE,
                    }
                )
            elif exercise_name in CUSTOM_EXERCISES:
                exercises.append(
                    {
                        "exercise_name": exercise_name,
                        **CUSTOM_EXERCISES[exercise_name],
                        "sets": 1,
                        "reps": effective_reps,
                        "weight_kg": weight_kg,
                        "rpe": DEFAULT_RPE,
                    }
                )

        load = plugin.compute_load(
            {"exercises": exercises}, intensity_modifier=1.0
        )
        daily_loads[date] = load

        print(
            f"{date:<12} {len(exercises):>5} {load.metabolic:>8.0f} "
            f"{load.neuromuscular:>8.0f} {load.tendineo:>8.0f} "
            f"{load.autonomic:>8.0f} {load.coordination:>8.0f}"
        )

    # ── ACWR Simulation ─────────────────────────────────────────────
    all_dates = sorted(daily_loads.keys())
    start_date = datetime.date.fromisoformat(all_dates[0])
    end_date = datetime.date.fromisoformat(all_dates[-1])

    # Check ACWR at each training date + weekly intervals
    check_dates: set[str] = set(all_dates)
    current = start_date
    while current <= end_date:
        check_dates.add(current.isoformat())
        current += datetime.timedelta(days=7)

    print()
    print("=" * 120)
    print(
        f"{'Date':<12} {'M':>7} {'N':>7} {'T':>7} {'A':>7} {'C':>7}"
        f"  {'Structural':<26} {'Global':<18} {'Note'}"
    )
    print("=" * 120)

    for check_str in sorted(check_dates):
        check_date = datetime.date.fromisoformat(check_str)

        acute_start = check_date - datetime.timedelta(days=6)
        chronic_start = check_date - datetime.timedelta(days=27)

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
            domain_results["neuromuscular"],
            domain_results["tendineo"],
        )
        global_status = _compute_global_status(
            acwr_vector, structural, cfg.domain_weights
        )
        context = _generate_context_note(acwr_vector, structural, global_status)

        trained = " <<<" if check_str in all_dates else ""

        parts = []
        for domain in DOMAIN_NAMES:
            dacwr = domain_results[domain]
            if dacwr.value is not None:
                parts.append(f"{dacwr.value:>7.2f}")
            else:
                parts.append(f"{'--':>7}")

        # Truncate context note for display
        ctx_short = context[:60] + "..." if len(context) > 60 else context

        print(
            f"{check_str:<12} {''.join(parts)}"
            f"  {structural:<26} {global_status:<18}{trained}"
        )

    # ── Summary ─────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Training days: {len(all_dates)}")
    print(f"Period: {all_dates[0]} to {all_dates[-1]}")
    print(f"Frequency: ~{len(all_dates) / 12:.1f} sessions/week")
    print()

    # Show context note for last training date
    check_date = datetime.date.fromisoformat(all_dates[-1])
    acute_start = check_date - datetime.timedelta(days=6)
    chronic_start = check_date - datetime.timedelta(days=27)
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
    print(f"Context note (as of {all_dates[-1]}):")
    print(f"  {context}")


if __name__ == "__main__":
    main()
