#!/usr/bin/env python3
"""
Convert a Health Auto Export JSON file to site/data/biometrics.jsonl.

Usage:
    python3 scripts/convert_health_export.py <export.json>
    python3 scripts/convert_health_export.py   # auto-detects newest HealthAutoExport*.json

Config is read from site/data/config.json — edit that file to change privacy rules,
targets, or challenge metadata. No hardcoded values in this script.
"""

import json
import sys
import os
from collections import defaultdict
from pathlib import Path

VAULT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = VAULT_ROOT / "site" / "data" / "config.json"
OUTPUT_PATH = VAULT_ROOT / "site" / "data" / "biometrics.jsonl"
JOURNAL_DIR = VAULT_ROOT / "journal"
JOURNAL_OUTPUT_PATH = VAULT_ROOT / "site" / "data" / "journal.jsonl"


def load_config():
    with open(CONFIG_PATH) as f:
        return json.load(f)


def parse_date(s):
    return s[:10]


def to_day_avg(records, key="qty"):
    by_day = defaultdict(list)
    for r in records:
        d = parse_date(r["date"])
        val = r.get(key)
        if val is not None:
            by_day[d].append(val)
    return {d: sum(v) / len(v) for d, v in by_day.items()}


def parse_journal_file(path):
    parts = path.stem.split(".")
    if len(parts) != 3:
        return None
    yyyy, mm, dd = parts
    if not (len(yyyy) == 4 and len(mm) == 2 and len(dd) == 2):
        return None

    text = path.read_text().strip()
    if not text:
        return {"date": f"{yyyy}-{mm}-{dd}", "title": "", "body": ""}

    lines = text.splitlines()
    first = next((line.strip() for line in lines if line.strip()), "")
    title = first.lstrip("#").strip() if first.startswith("#") else first

    if first.startswith("#"):
        body_lines = lines[1:]
    else:
        body_lines = lines
    body = "\n".join(body_lines).strip()

    return {"date": f"{yyyy}-{mm}-{dd}", "title": title, "body": body}


def write_journal_index():
    entries = []
    if JOURNAL_DIR.exists():
        for path in sorted(JOURNAL_DIR.glob("*.md")):
            entry = parse_journal_file(path)
            if entry:
                entries.append(entry)

    JOURNAL_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL_OUTPUT_PATH, "w") as f:
        if entries:
            f.write("\n".join(json.dumps(entry, separators=(",", ":")) for entry in entries) + "\n")
        else:
            f.write("")

    print(f"  Written {len(entries)} journal entries → {JOURNAL_OUTPUT_PATH}")


def convert(export_path, cfg):
    with open(export_path) as f:
        raw = json.load(f)

    excluded = set(cfg["privacy"].get("exclude_metrics", []))

    metrics = {}
    for m in raw["data"]["metrics"]:
        name = m.get("name", m.get("units", "unknown"))
        if name in excluded:
            print(f"  [privacy] Skipping {name} — excluded by config")
            continue
        metrics[name] = m["data"]

    weight      = to_day_avg(metrics.get("weight_body_mass", []))
    bf_pct      = to_day_avg(metrics.get("body_fat_percentage", []))
    lean_mass   = to_day_avg(metrics.get("lean_body_mass", []))
    hrv         = to_day_avg(metrics.get("heart_rate_variability", []))
    rhr         = to_day_avg(metrics.get("resting_heart_rate", []))
    active_kcal = to_day_avg(metrics.get("active_energy", []))
    basal_kcal  = to_day_avg(metrics.get("basal_energy_burned", []))
    dietary_kcal = to_day_avg(metrics.get("dietary_energy", []))
    protein_g   = to_day_avg(metrics.get("protein", []))
    fat_g       = to_day_avg(metrics.get("total_fat", []))
    carbs_g     = to_day_avg(metrics.get("carbohydrates", []))
    spo2        = to_day_avg(metrics.get("blood_oxygen_saturation", []))
    vo2         = to_day_avg(metrics.get("vo2_max", []))

    hr_by_day = defaultdict(list)
    for r in metrics.get("heart_rate", []):
        d = parse_date(r["date"])
        if r.get("Avg") is not None:
            hr_by_day[d].append({"avg": r["Avg"], "max": r.get("Max"), "min": r.get("Min")})
    hr_daily = {
        d: {
            "avg": round(sum(x["avg"] for x in v) / len(v), 1),
            "max": max(x["max"] for x in v if x["max"]),
            "min": min(x["min"] for x in v if x["min"]),
        }
        for d, v in hr_by_day.items()
    }

    sleep_daily = {}
    for r in metrics.get("sleep_analysis", []):
        d = parse_date(r["date"])
        sleep_daily[d] = {
            "total_hr": round(r.get("totalSleep", r.get("inBed", 0)), 2),
            "deep_hr":  round(r.get("deep", 0), 2),
            "rem_hr":   round(r.get("rem", 0), 2),
            "core_hr":  round(r.get("core", 0), 2),
            "awake_hr": round(r.get("awake", 0), 2),
        }

    all_dates = sorted(set(
        list(weight)
        + list(bf_pct)
        + list(lean_mass)
        + list(hrv)
        + list(rhr)
        + list(active_kcal)
        + list(basal_kcal)
        + list(dietary_kcal)
        + list(protein_g)
        + list(fat_g)
        + list(carbs_g)
        + list(spo2)
        + list(vo2)
        + list(hr_daily)
        + list(sleep_daily)
    ))

    def r2(v):
        return round(v, 2) if v is not None else None

    lines = []
    for d in all_dates:
        raw_bf = bf_pct.get(d)
        bf = round(raw_bf if raw_bf and raw_bf > 1 else (raw_bf * 100 if raw_bf else None), 2) if raw_bf else None
        w = weight.get(d)
        fat_mass = round(w * bf / 100, 2) if w and bf else None
        lean_computed = round(w - fat_mass, 2) if w and fat_mass else r2(lean_mass.get(d))
        sl = sleep_daily.get(d, {})
        hr = hr_daily.get(d, {})

        rec = {
            "date": d,
            "body": {
                "weight_lbs":    r2(w),
                "body_fat_pct":  bf,
                "fat_mass_lbs":  fat_mass,
                "lean_mass_lbs": lean_computed,
            },
            "recovery": {
                "hrv_sdnn_ms":    r2(hrv.get(d)),
                "resting_hr_bpm": r2(rhr.get(d)),
                "spo2_pct":       r2(spo2.get(d)),
                "vo2_max":        r2(vo2.get(d)),
            },
            "heart_rate": {
                "avg_bpm": hr.get("avg"),
                "max_bpm": hr.get("max"),
                "min_bpm": hr.get("min"),
            } if hr else None,
            "sleep": {
                "total_hr": sl.get("total_hr"),
                "deep_hr":  sl.get("deep_hr"),
                "rem_hr":   sl.get("rem_hr"),
                "core_hr":  sl.get("core_hr"),
                "awake_hr": sl.get("awake_hr"),
            } if sl else None,
            "activity": {
                "active_burn_kcal": r2(active_kcal.get(d)),
                "basal_burn_kcal": r2(basal_kcal.get(d)),
            },
            "nutrition": {
                "calories_kcal": r2(dietary_kcal.get(d)),
                "protein_g": r2(protein_g.get(d)),
                "fat_g": r2(fat_g.get(d)),
                "carbs_g": r2(carbs_g.get(d)),
            },
            "flags": [],
            "notes": "",
        }
        lines.append(json.dumps(rec, separators=(",", ":")))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"  Written {len(lines)} records → {OUTPUT_PATH}")
    write_journal_index()


if __name__ == "__main__":
    cfg = load_config()
    print(f"Config loaded: {cfg['challenge']['name']} — {cfg['challenge']['athlete']} — start {cfg['challenge']['start_date']}")

    if len(sys.argv) < 2:
        exports = sorted(VAULT_ROOT.glob("HealthAutoExport*.json"), key=os.path.getmtime, reverse=True)
        if not exports:
            print("Usage: python3 scripts/convert_health_export.py <export.json>")
            print("Or drop a HealthAutoExport*.json in the vault root.")
            sys.exit(1)
        export_path = exports[0]
        print(f"Auto-detected: {export_path.name}")
    else:
        export_path = Path(sys.argv[1])

    print(f"Converting {export_path.name}...")
    convert(export_path, cfg)
    print("Done.")
