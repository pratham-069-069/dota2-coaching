import pandas as pd
from typing import Optional, Dict
from src.data.config import RAW_DATA_DIR, COMPETITIVE_GAME_MODES

def load_hero_names() -> pd.DataFrame:
    """Loads hero IDs, system names, and localized names."""
    path = RAW_DATA_DIR / "hero_names.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["hero_id", "name", "localized_name"])

def get_hero_dict() -> Dict[int, str]:
    """Returns a dictionary mapping hero_id -> localized_name."""
    df = load_hero_names()
    if not df.empty and "hero_id" in df.columns and "localized_name" in df.columns:
        return dict(zip(df["hero_id"], df["localized_name"]))
    return {}

def load_item_names() -> pd.DataFrame:
    """Loads item ID to item name mappings."""
    path = RAW_DATA_DIR / "item_ids.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["item_id", "item_name"])

def get_item_dict() -> Dict[int, str]:
    """Returns a dictionary mapping item_id -> item_name."""
    df = load_item_names()
    if not df.empty and "item_id" in df.columns and "item_name" in df.columns:
        return dict(zip(df["item_id"], df["item_name"]))
    return {}

def load_matches(competitive_only: bool = True, nrows: Optional[int] = None) -> pd.DataFrame:
    """
    Loads match metadata.
    Filters by competitive game modes if competitive_only is True.
    """
    path = RAW_DATA_DIR / "match.csv"
    df = pd.read_csv(path, nrows=nrows)
    if competitive_only and "game_mode" in df.columns:
        df = df[df["game_mode"].isin(COMPETITIVE_GAME_MODES)].copy()
    return df

def load_players(match_ids: Optional[set] = None, nrows: Optional[int] = None) -> pd.DataFrame:
    """
    Loads player performance records.
    Optionally filters by an existing set of match_ids.
    """
    path = RAW_DATA_DIR / "players.csv"
    if match_ids is not None:
        # Load in chunks to save memory if match_ids are specified
        chunks = []
        for chunk in pd.read_csv(path, chunksize=100000):
            filtered = chunk[chunk["match_id"].isin(match_ids)]
            if not filtered.empty:
                chunks.append(filtered)
        return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()
    return pd.read_csv(path, nrows=nrows)

def load_player_ratings() -> pd.DataFrame:
    """Loads player TrueSkill mu, sigma, total wins, and total matches."""
    path = RAW_DATA_DIR / "player_ratings.csv"
    return pd.read_csv(path)

def load_objectives(nrows: Optional[int] = None) -> pd.DataFrame:
    """Loads objective logs (towers, roshan, first bloods)."""
    path = RAW_DATA_DIR / "objectives.csv"
    return pd.read_csv(path, nrows=nrows)

def load_teamfights(nrows: Optional[int] = None) -> pd.DataFrame:
    """Loads teamfight event records."""
    path = RAW_DATA_DIR / "teamfights.csv"
    return pd.read_csv(path, nrows=nrows)

def load_teamfights_players(nrows: Optional[int] = None) -> pd.DataFrame:
    """Loads per-player teamfight performance."""
    path = RAW_DATA_DIR / "teamfights_players.csv"
    return pd.read_csv(path, nrows=nrows)
