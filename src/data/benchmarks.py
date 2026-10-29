"""
Hero Benchmarks Generator:
Computes empirical distribution quantiles (p10, p25, p50, p75, p90) for all Dota 2 heroes
across all 500,000 player-match records in competitive matches.
Used by the Between-Match Coach for player performance diagnostics.
"""

import logging
import json
import numpy as np
import pandas as pd
from src.data.config import RAW_DATA_DIR, FEATURES_DIR
from src.data.loaders import load_hero_names

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BENCHMARK_COLS = [
    "gold_per_min",
    "xp_per_min",
    "kills",
    "deaths",
    "assists",
    "last_hits",
    "denies",
    "hero_damage",
    "tower_damage",
    "stuns",
]


def compute_hero_benchmarks() -> pd.DataFrame:
    logger.info("Loading players.csv for benchmark computations...")
    players_path = RAW_DATA_DIR / "players.csv"
    hero_names_df = load_hero_names()
    hero_map = dict(zip(hero_names_df["hero_id"], hero_names_df["localized_name"]))

    # Read necessary columns
    usecols = ["hero_id"] + BENCHMARK_COLS
    chunks = []
    for chunk in pd.read_csv(players_path, usecols=usecols, chunksize=100000):
        # fill na for stuns
        chunk["stuns"] = chunk["stuns"].fillna(0.0)
        chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    logger.info(f"Loaded {len(df)} player records. Calculating quantiles per hero...")

    benchmarks = []
    quantiles = [0.10, 0.25, 0.50, 0.75, 0.90]

    for hid, group in df.groupby("hero_id"):
        if len(group) < 10:
            continue
        entry = {
            "hero_id": int(hid),
            "hero_name": hero_map.get(int(hid), f"Hero {hid}"),
            "sample_size": len(group),
        }
        for col in BENCHMARK_COLS:
            vals = group[col].dropna()
            if len(vals) == 0:
                continue
            entry[f"{col}_mean"] = round(float(vals.mean()), 2)
            entry[f"{col}_std"] = round(float(vals.std()), 2)
            for q in quantiles:
                q_name = f"p{int(q*100)}"
                entry[f"{col}_{q_name}"] = round(float(vals.quantile(q)), 2)

        benchmarks.append(entry)

    bench_df = pd.DataFrame(benchmarks)
    parquet_path = FEATURES_DIR / "hero_benchmarks.parquet"
    json_path = FEATURES_DIR / "hero_benchmarks.json"
    bench_df.to_parquet(parquet_path, index=False)
    bench_df.to_json(json_path, orient="records", indent=2)

    logger.info(f"Computed benchmarks for {len(bench_df)} heroes. Saved to {parquet_path} and {json_path}")
    return bench_df


if __name__ == "__main__":
    compute_hero_benchmarks()
