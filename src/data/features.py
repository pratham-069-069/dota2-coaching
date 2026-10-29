"""
Feature engineering module for Dota 2 Coaching Intelligence Platform.
Computes hero win rates, synergy matrices, counter matrices,
and match draft representation vectors.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

from src.data.config import RAW_DATA_DIR, FEATURES_DIR, RADIANT_SLOTS, DIRE_SLOTS
from src.data.loaders import load_hero_names, load_matches, load_players

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

HERO_NAMES_DF = load_hero_names()
HERO_ID_TO_NAME = dict(zip(HERO_NAMES_DF["hero_id"], HERO_NAMES_DF["localized_name"]))
NAME_TO_HERO_ID = dict(zip(HERO_NAMES_DF["localized_name"], HERO_NAMES_DF["hero_id"]))
ALL_HERO_IDS = sorted(list(HERO_NAMES_DF["hero_id"].unique()))
NUM_HEROES = len(ALL_HERO_IDS)
HERO_ID_TO_IDX = {hid: idx for idx, hid in enumerate(ALL_HERO_IDS)}
IDX_TO_HERO_ID = {idx: hid for idx, hid in enumerate(ALL_HERO_IDS)}


def extract_match_drafts(nrows_matches: Optional[int] = None) -> pd.DataFrame:
    """
    Extracts Radiant and Dire hero drafts for each match.
    Returns DataFrame with columns:
      - match_id
      - radiant_win (0 or 1)
      - radiant_heroes (list of 5 hero_ids)
      - dire_heroes (list of 5 hero_ids)
    """
    logger.info("Loading matches and players for draft extraction...")
    matches_df = load_matches(competitive_only=True, nrows=nrows_matches)[["match_id", "radiant_win"]]
    valid_match_ids = set(matches_df["match_id"].unique())

    # Read players.csv in chunks to be memory-efficient
    players_path = RAW_DATA_DIR / "players.csv"
    chunks = []
    for chunk in pd.read_csv(players_path, usecols=["match_id", "player_slot", "hero_id"], chunksize=100000):
        filtered = chunk[chunk["match_id"].isin(valid_match_ids)]
        if not filtered.empty:
            chunks.append(filtered)
    players_df = pd.concat(chunks, ignore_index=True)

    # Classify side
    players_df["is_radiant"] = players_df["player_slot"].isin(RADIANT_SLOTS)

    # Group by match_id
    rad_grouped = (
        players_df[players_df["is_radiant"]]
        .groupby("match_id")["hero_id"]
        .apply(list)
        .reset_index(name="radiant_heroes")
    )
    dire_grouped = (
        players_df[~players_df["is_radiant"]]
        .groupby("match_id")["hero_id"]
        .apply(list)
        .reset_index(name="dire_heroes")
    )

    drafts_df = matches_df.merge(rad_grouped, on="match_id", how="inner")
    drafts_df = drafts_df.merge(dire_grouped, on="match_id", how="inner")

    # Filter to matches that have exactly 5 heroes on both sides
    drafts_df["rad_count"] = drafts_df["radiant_heroes"].apply(len)
    drafts_df["dire_count"] = drafts_df["dire_heroes"].apply(len)
    clean_drafts = drafts_df[(drafts_df["rad_count"] == 5) & (drafts_df["dire_count"] == 5)].copy()
    clean_drafts["radiant_win"] = clean_drafts["radiant_win"].astype(int)

    logger.info(f"Extracted {len(clean_drafts)} clean 5v5 drafts from {len(matches_df)} matches.")
    return clean_drafts[["match_id", "radiant_win", "radiant_heroes", "dire_heroes"]]


def compute_hero_analytics(drafts_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Computes:
      1. Individual hero stats (picks, wins, win_rate)
      2. Hero synergy matrix (win rate when hero A & B are teammates)
      3. Hero counter matrix (win rate & advantage when hero A plays against hero B)
    """
    logger.info("Computing hero individual stats, synergy matrix, and counter matrix...")
    hero_picks = {hid: 0 for hid in ALL_HERO_IDS}
    hero_wins = {hid: 0 for hid in ALL_HERO_IDS}

    # Pairwise synergy: (min_id, max_id) -> [wins, total_games]
    synergy_counts: Dict[Tuple[int, int], List[int]] = {}
    # Pairwise counter: (hero_a, hero_b) -> [a_wins, total_games] (A vs B)
    counter_counts: Dict[Tuple[int, int], List[int]] = {}

    for _, row in drafts_df.iterrows():
        rad_win = row["radiant_win"]
        rad_heroes = row["radiant_heroes"]
        dire_heroes = row["dire_heroes"]

        # Radiant team
        for h in rad_heroes:
            hero_picks[h] = hero_picks.get(h, 0) + 1
            if rad_win == 1:
                hero_wins[h] = hero_wins.get(h, 0) + 1

        # Dire team
        for h in dire_heroes:
            hero_picks[h] = hero_picks.get(h, 0) + 1
            if rad_win == 0:
                hero_wins[h] = hero_wins.get(h, 0) + 1

        # Radiant synergy pairs
        for i in range(len(rad_heroes)):
            for j in range(i + 1, len(rad_heroes)):
                pair = tuple(sorted((rad_heroes[i], rad_heroes[j])))
                if pair not in synergy_counts:
                    synergy_counts[pair] = [0, 0]
                synergy_counts[pair][1] += 1
                if rad_win == 1:
                    synergy_counts[pair][0] += 1

        # Dire synergy pairs
        for i in range(len(dire_heroes)):
            for j in range(i + 1, len(dire_heroes)):
                pair = tuple(sorted((dire_heroes[i], dire_heroes[j])))
                if pair not in synergy_counts:
                    synergy_counts[pair] = [0, 0]
                synergy_counts[pair][1] += 1
                if rad_win == 0:
                    synergy_counts[pair][0] += 1

        # Counter pairs (Radiant vs Dire)
        for h_rad in rad_heroes:
            for h_dire in dire_heroes:
                # h_rad vs h_dire
                pair_r_vs_d = (h_rad, h_dire)
                if pair_r_vs_d not in counter_counts:
                    counter_counts[pair_r_vs_d] = [0, 0]
                counter_counts[pair_r_vs_d][1] += 1
                if rad_win == 1:
                    counter_counts[pair_r_vs_d][0] += 1

                # h_dire vs h_rad
                pair_d_vs_r = (h_dire, h_rad)
                if pair_d_vs_r not in counter_counts:
                    counter_counts[pair_d_vs_r] = [0, 0]
                counter_counts[pair_d_vs_r][1] += 1
                if rad_win == 0:
                    counter_counts[pair_d_vs_r][0] += 1

    # 1. Hero stats dataframe
    hero_stats_list = []
    total_matches = len(drafts_df)
    for hid in ALL_HERO_IDS:
        picks = hero_picks.get(hid, 0)
        wins = hero_wins.get(hid, 0)
        wr = (wins / picks) if picks > 0 else 0.5
        pick_rate = (picks / (total_matches * 10)) if total_matches > 0 else 0.0
        hero_stats_list.append({
            "hero_id": hid,
            "localized_name": HERO_ID_TO_NAME.get(hid, f"Hero {hid}"),
            "picks": picks,
            "wins": wins,
            "win_rate": round(wr, 4),
            "pick_rate": round(pick_rate, 4),
        })
    hero_stats_df = pd.DataFrame(hero_stats_list)
    hero_wr_dict = dict(zip(hero_stats_df["hero_id"], hero_stats_df["win_rate"]))

    # 2. Synergy dataframe
    synergy_list = []
    for (h1, h2), (w, tot) in synergy_counts.items():
        if tot >= 5:  # Minimum sample filter
            pair_wr = w / tot
            expected_wr = (hero_wr_dict.get(h1, 0.5) + hero_wr_dict.get(h2, 0.5)) / 2
            synergy_score = pair_wr - expected_wr  # Above expected win rate
            synergy_list.append({
                "hero_1": h1,
                "hero_2": h2,
                "hero_1_name": HERO_ID_TO_NAME.get(h1, f"Hero {h1}"),
                "hero_2_name": HERO_ID_TO_NAME.get(h2, f"Hero {h2}"),
                "games": tot,
                "wins": w,
                "win_rate": round(pair_wr, 4),
                "synergy_score": round(synergy_score, 4),
            })
    synergy_df = pd.DataFrame(synergy_list)

    # 3. Counter dataframe (A vs B)
    counter_list = []
    for (h_a, h_b), (w, tot) in counter_counts.items():
        if tot >= 5:
            matchup_wr = w / tot
            base_wr_a = hero_wr_dict.get(h_a, 0.5)
            counter_advantage = matchup_wr - base_wr_a  # Performance delta against B
            counter_list.append({
                "hero": h_a,
                "opponent": h_b,
                "hero_name": HERO_ID_TO_NAME.get(h_a, f"Hero {h_a}"),
                "opponent_name": HERO_ID_TO_NAME.get(h_b, f"Hero {h_b}"),
                "games": tot,
                "wins": w,
                "win_rate": round(matchup_wr, 4),
                "advantage": round(counter_advantage, 4),
            })
    counter_df = pd.DataFrame(counter_list)

    return hero_stats_df, synergy_df, counter_df


def build_draft_feature_matrix(drafts_df: pd.DataFrame, hero_stats_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """
    Transforms drafts into high-dimensional feature vectors for ML models.
    Features:
      - 112 hero differential features (+1 Radiant, -1 Dire, 0 unpicked)
      - Radiant team avg win rate, Dire team avg win rate, differential
      - Radiant team pick rate sum, Dire team pick rate sum
    """
    num_samples = len(drafts_df)
    hero_wr_map = dict(zip(hero_stats_df["hero_id"], hero_stats_df["win_rate"]))
    hero_pr_map = dict(zip(hero_stats_df["hero_id"], hero_stats_df["pick_rate"]))

    # Hero diff features
    X_diff = np.zeros((num_samples, NUM_HEROES), dtype=np.float32)
    # Aggregate summary features: [rad_avg_wr, dire_avg_wr, wr_diff, rad_pr_sum, dire_pr_sum]
    X_agg = np.zeros((num_samples, 5), dtype=np.float32)
    y = drafts_df["radiant_win"].to_numpy(dtype=np.int32)

    for i, (_, row) in enumerate(drafts_df.iterrows()):
        rad = row["radiant_heroes"]
        dire = row["dire_heroes"]

        for h in rad:
            if h in HERO_ID_TO_IDX:
                X_diff[i, HERO_ID_TO_IDX[h]] = 1.0

        for h in dire:
            if h in HERO_ID_TO_IDX:
                X_diff[i, HERO_ID_TO_IDX[h]] = -1.0

        rad_wrs = [hero_wr_map.get(h, 0.5) for h in rad]
        dire_wrs = [hero_wr_map.get(h, 0.5) for h in dire]
        rad_prs = [hero_pr_map.get(h, 0.05) for h in rad]
        dire_prs = [hero_pr_map.get(h, 0.05) for h in dire]

        r_wr_avg = float(np.mean(rad_wrs))
        d_wr_avg = float(np.mean(dire_wrs))
        X_agg[i, 0] = r_wr_avg
        X_agg[i, 1] = d_wr_avg
        X_agg[i, 2] = r_wr_avg - d_wr_avg
        X_agg[i, 3] = float(np.sum(rad_prs))
        X_agg[i, 4] = float(np.sum(dire_prs))

    feature_names = [f"hero_{hid}_{HERO_ID_TO_NAME.get(hid, hid).replace(' ', '_')}" for hid in ALL_HERO_IDS]
    feature_names.extend(["rad_avg_wr", "dire_avg_wr", "wr_diff", "rad_pr_sum", "dire_pr_sum"])

    X = np.hstack([X_diff, X_agg])
    return X, y, feature_names


def prepare_and_save_all_features() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Orchestrates feature calculation and saves results into parquet/json."""
    logger.info("Extracting match drafts...")
    drafts_df = extract_match_drafts()
    drafts_path = FEATURES_DIR / "match_drafts.parquet"
    drafts_df.to_parquet(drafts_path, index=False)
    logger.info(f"Saved match drafts to {drafts_path}")

    hero_stats_df, synergy_df, counter_df = compute_hero_analytics(drafts_df)

    hero_stats_df.to_parquet(FEATURES_DIR / "hero_stats.parquet", index=False)
    synergy_df.to_parquet(FEATURES_DIR / "hero_synergy.parquet", index=False)
    counter_df.to_parquet(FEATURES_DIR / "hero_counter.parquet", index=False)

    # Save as JSON lookup files for ultra-fast API retrieval
    hero_stats_df.to_json(FEATURES_DIR / "hero_stats.json", orient="records", indent=2)
    synergy_df.to_json(FEATURES_DIR / "hero_synergy.json", orient="records", indent=2)
    counter_df.to_json(FEATURES_DIR / "hero_counter.json", orient="records", indent=2)

    logger.info("Saved hero stats, synergy, and counter features to parquet & JSON.")
    return drafts_df, hero_stats_df, synergy_df, counter_df


if __name__ == "__main__":
    prepare_and_save_all_features()
