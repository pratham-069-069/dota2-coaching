from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw" if (DATA_DIR / "raw").exists() else ROOT_DIR
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
MODELS_DIR = ROOT_DIR / "models"
CONFIGS_DIR = ROOT_DIR / "configs"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FEATURES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
CONFIGS_DIR.mkdir(parents=True, exist_ok=True)

# Standard Competitive Game Modes
# 1: All Pick, 2: Captains Mode, 22: Ranked All Pick
COMPETITIVE_GAME_MODES = [1, 2, 22]

# Dota 2 Player Slots: 0-4 are Radiant, 128-132 are Dire
RADIANT_SLOTS = [0, 1, 2, 3, 4]
DIRE_SLOTS = [128, 129, 130, 131, 132]

# Role Archetypes for Dota 2
ROLES = {
    1: "Safe Lane Carry (Pos 1)",
    2: "Mid Laner (Pos 2)",
    3: "Offlaner (Pos 3)",
    4: "Soft Support (Pos 4)",
    5: "Hard Support (Pos 5)"
}
