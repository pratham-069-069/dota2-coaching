# 🔍 `gemin.md` — Full Code-Verified Review for Claude

> **Purpose:** Written by Gemini after a full audit of the live codebase at `e:\Dota2\`.
> Every claim in `gemin.md` was cross-referenced against the actual source files.
> **Read this before touching any code** so you don't repeat mistakes or reinvent existing utilities.
>
> **Date written:** 2026-10-18

---

## ✅ SECTION 1 — What `gemin.md` Gets Right (Don't Change These)

| Claim | Verified Against |
|---|---|
| XGBoost hyperparams (n_estimators=180, lr=0.08, max_depth=5, subsample=0.8, colsample=0.8) | `src/models/draft_advisor.py` |
| AUC=0.6378, Accuracy=59.95%, LogLoss=0.6633 | `models/draft_model_meta.json` — exact match |
| 117-feature vector: 112 hero differentials + 5 meta features | `src/data/features.py` `build_draft_feature_matrix()` |
| Empirical quantile benchmarks p10–p90 via `np.interp` | `coach_engine.py` `_estimate_percentile()` L46–L73 |
| TrueSkill MMR: `max(500, (mu - 2*sigma) * 150)` | `player_profiler.py` L55 — exact |
| Resource Conflict at ≥3 players with Farming Tempo > 65 | `player_profiler.py` L332–333 |
| Utility Gap when max utility < 55 | `player_profiler.py` L336 |
| 6 radar dimensions (Aggression, Farming Tempo, Objective Push, Team Utility, Survivability, Versatility) | `player_profiler.py` L104–111 |
| Synergy / Counter matrix formulas | `src/data/features.py` |
| All 8 FastAPI endpoints listed | `src/api/main.py` — all verified |
| All 10 `data/features/` artifact files | Disk directory confirmed |
| 19-test suite, all test names | `tests/test_platform.py` L305–324 |
| CORS `allow_origins=["*"]` | `main.py` L33 |
| Item Advisor 4 threat categories and counter items | `item_advisor.py` `SITUATIONAL_COUNTERS` |

---

## ⚠️ SECTION 2 — Errors & Inaccuracies in `gemin.md`

### Error 1: Model 2 numbering gap is never explained

`gemin.md` lists Model 1, Model 3, Model 4, Model 5 — **Model 2 is skipped with no explanation**.

**Reality:** Model 2 was a planned "meta win-rate baseline" that was absorbed into Model 1's feature engineering — specifically the 5 aggregate meta features (`rad_avg_wr`, `dire_avg_wr`, `wr_diff`, `rad_pr_sum`, `dire_pr_sum`) in the 117-d vector. It was never built as a separate component. Don't look for it.

---

### Error 2: Item Advisor hero lists are incomplete

`gemin.md` describes:
- *"High Evasion threats (PA, Windranger, Brewmaster)"*
- *"Tank / Armor frontline (Centaur, Axe, Bristleback)"*
- *"Right-Click Hyper-Carries (Sven, Ursa, Juggernaut)"*

**Actual code in `item_advisor.py` `SITUATIONAL_COUNTERS`:**
```python
"evasion_threats":        heroes = [44, 21, 32, 78]     # PA, Windranger, RIKI, Brewmaster
"magic_cc_threats":       heroes = [26, 25, 27, 17, 74]  # Lion, Lina, Shadow Shaman, Storm, Invoker
"tank_threats":           heroes = [96, 14, 2, 99, 29]   # Centaur, PUDGE, Axe, Bristleback, TIDEHUNTER
"physical_carry_threats": heroes = [18, 70, 44, 8, 28]   # Sven, Ursa, PA, Juggernaut, SLARDAR
```

**Missing from `gemin.md`:** Riki (evasion), Pudge + Tidehunter (tank), Slardar (physical carry).

---

### Error 3: Core item timing table is missing 3 entries

`gemin.md` lists 4 item timings. **`item_advisor.py` `CORE_ITEM_TIMINGS` has 6:**

```python
"black_king_bar":   target_min=21, gold=3975  # in gemin.md
"blink":            target_min=14, gold=2250  # in gemin.md
"manta":            target_min=22, gold=4950  # ← MISSING
"ultimate_scepter": target_min=20, gold=4200  # in gemin.md
"desolator":        target_min=18, gold=3500  # ← MISSING
"orchid":           target_min=17, gold=4075  # ← MISSING
```

---

### Error 4: Two separate archetype classification paths exist — only one documented

`gemin.md` makes the archetype system sound like a single algorithm. **It has two completely different code paths:**

**Path A — Real match data** (used when account has ≥2 match records in `player_matches.parquet`):
- `profile_player_matches()` called internally by `get_player_full_profile()`
- Computes radar scores from actual GPM, kills, deaths, tower damage, stuns, hero diversity entropy
- **This is real empirical data.**

**Path B — Hash-seeded fallback** (used when <2 match records exist):
- Runs inside `get_player_full_profile()` L92–169
- Radar scores are synthetically estimated:
  ```python
  seed = abs(hash(str(account_id))) % 100
  aggro = float(np.clip(50 + (mu - 25) * 4 + (seed % 20 - 10), 20, 95))
  ```
- Output **looks real but is deterministic pseudo-data** seeded by TrueSkill mu/sigma + hash of account_id.
- **Do NOT use this for real scouting.** It is only for UI demos with unknown accounts.

**How to tell which path ran:** If `top_comfort_heroes` contains exactly 3 hardcoded heroes (Anti-Mage, Axe, CM, etc.), the fallback ran. If it contains real hero IDs with real match counts, real data was used.

---

### Error 5: `player_matches.parquet` file size is misstated

`gemin.md` says: `9.48 MB`
Actual disk: `9,943,242 bytes` = **9.48 MiB** (mebibytes) or **9.94 MB** (megabytes).
This is an MB vs MiB confusion — the file is 9.94 MB. Minor, but worth knowing.

---

### Error 6: `test_get_match_players(0)` doesn't actually test match ID 0

`tests/test_platform.py` L164 calls `get_match_players(0)`.

`player_profiler.py` L180 logic:
```python
if match_id < 0 or match_id not in all_match_ids:
    match_id = int(np.random.choice(all_match_ids[:2000]))  # RANDOM
```

Match ID `0` is not in the dataset, so the function picks a **random match** every time. The test still passes because it only asserts `player_count == 10`, never verifying which match was returned.

**In practice:** `GET /match/0/players` returns a random match. Use `match_id=-1` explicitly for random, or a real competitive match ID for a specific one.

---

### Error 7: Hero-specific item timing overrides are undocumented

`coach_engine.py` `get_hero_matrix()` L287–300 has **hardcoded per-hero timing overrides**:

```python
if hero_id == 1:          # Anti-Mage: Battle Fury 13-15, Manta 20-22, Basher 26-28, BKB situational
elif hero_id in [8, 44]:  # Juggernaut / PA: Phase Boots 12-15, Manta/BKB 20-22, Skadi/Basher 26-30
# all other heroes → generic 4-item timing list
```

To add timings for more heroes, insert another `elif hero_id in [...]` block before line 301.

---

## ❌ SECTION 3 — Missing from `gemin.md` Entirely

### Missing 1: `src/data/config.py` — path constants (most important missing piece)

Every module imports from here. **Always use these; never hardcode paths.**

```python
from src.data.config import ROOT_DIR, RAW_DATA_DIR, FEATURES_DIR, MODELS_DIR

ROOT_DIR     = Path(__file__).parent.parent.parent  # e:\Dota2\
RAW_DATA_DIR = ROOT_DIR         # ← Raw CSVs are in ROOT, not data/raw/
FEATURES_DIR = ROOT_DIR / "data" / "features"       # all parquet + JSON files
MODELS_DIR   = ROOT_DIR / "models"                  # pkl + meta.json
PROCESSED_DIR = ROOT_DIR / "data" / "processed"     # empty / unused
CONFIGS_DIR  = ROOT_DIR / "configs"                 # empty / unused

COMPETITIVE_GAME_MODES = [1, 2, 22]  # All Pick, Captains Mode, Ranked All Pick
RADIANT_SLOTS = [0, 1, 2, 3, 4]
DIRE_SLOTS    = [128, 129, 130, 131, 132]
```

---

### Missing 2: Raw CSV files are in the PROJECT ROOT (non-standard!)

All raw data CSVs live at `e:\Dota2\` (the root), **not** in `data/raw/`. This is non-standard.
`config.py` handles this by setting `RAW_DATA_DIR = ROOT_DIR`.

**Files currently used:**
```
match.csv              2.7 MB   — match metadata + game mode + radiant_win
players.csv           130 MB   — 500k player-match records (GPM, XPM, KDA, LH, damage...)
player_ratings.csv    41.9 MB  — 834k TrueSkill ratings (mu, sigma, total_matches, total_wins)
hero_names.csv         4.2 KB  — hero_id → localized_name
item_ids.csv           3.0 KB  — item_id → item_name
```

**Files in root but NOT currently used by any model:**
```
purchase_log.csv      297 MB   — per-match item purchase timelines
player_time.csv       319 MB   — per-minute player state
ability_upgrades.csv  187 MB   — skill build order per match
chat.csv               52.7 MB — in-game chat
match_outcomes.csv    107 MB   — detailed outcomes
objectives.csv         60 MB   — tower kills, Roshan, first blood
teamfights.csv         11.8 MB — teamfight events
teamfights_players.csv 170 MB  — per-player teamfight metrics
```

These unused CSVs are a **rich future data source** (e.g. purchase_log could power a real ML item advisor instead of the current rule-based one).

---

### Missing 3: `src/data/loaders.py` — data loading helpers

Use these instead of raw `pd.read_csv()` calls:

```python
from src.data.loaders import (
    load_hero_names,         # → DataFrame: hero_id, name, localized_name
    get_hero_dict,           # → Dict[int, str]: hero_id → localized_name
    load_item_names,         # → DataFrame: item_id, item_name
    get_item_dict,           # → Dict[int, str]: item_id → item_name  (used by ItemAdvisor)
    load_matches,            # → DataFrame, competitive_only=True filters to game modes [1,2,22]
    load_players,            # → DataFrame, supports match_id set filtering with chunked reads
    load_player_ratings,     # → DataFrame: account_id, trueskill_mu, trueskill_sigma, total_wins, total_matches
    load_objectives,         # → DataFrame (nrows param supported)
    load_teamfights,         # → DataFrame (nrows param supported)
    load_teamfights_players, # → DataFrame (nrows param supported)
)
```

---

### Missing 4: How to regenerate precomputed features

If the dataset changes or you add new metrics, regenerate the parquet files:

```bash
# Regenerate hero benchmarks (p10-p90 quantiles per hero per metric)
python -c "from src.data.benchmarks import compute_and_save_benchmarks; compute_and_save_benchmarks()"

# Regenerate hero stats, synergy matrix, counter matrix, and match_drafts.parquet
python -c "from src.data.features import run_feature_pipeline; run_feature_pipeline()"

# Re-train the XGBoost draft model (do this LAST, after features are ready)
python -c "from src.models.draft_advisor import DraftAdvisor; a = DraftAdvisor(); a.train()"
```

**Warning:** Re-training overwrites `models/draft_xgb_model.pkl`. The current trained model achieves AUC=0.6378. Only re-train if you have a reason to expect improvement.

---

### Missing 5: Dual parquet + JSON artifact storage pattern

Every feature table has two formats:

| Parquet (runtime) | JSON (debug/inspect) |
|---|---|
| `hero_benchmarks.parquet` 78 KB | `hero_benchmarks.json` 211 KB |
| `hero_synergy.parquet` 90 KB | `hero_synergy.json` 1.1 MB |
| `hero_counter.parquet` 154 KB | `hero_counter.json` 2.2 MB |
| `hero_stats.parquet` 8.6 KB | `hero_stats.json` 15.8 KB |
| `player_matches.parquet` 9.94 MB | *(no JSON — too large)* |
| `match_drafts.parquet` 751 KB | *(no JSON — too large)* |

**Python code loads parquet at startup.** The JSON files are for human inspection only — open them in any text editor to browse.

---

### Missing 6: `data/processed/` and `configs/` are empty

Both directories exist (auto-created by `config.py`) but are completely empty. Don't look for data there.

---

### Missing 7: Frontend `api.js` — all client-side API functions

`frontend/src/services/api.js` is the **single source of truth** for all frontend ↔ backend communication.

**Base URL (line 1):** `const API_BASE = "http://localhost:8000"` — change for production.

All exported functions:

```javascript
fetchHealth()                                          // GET  /health
fetchHeroes()                                          // GET  /heroes → heroes[]
predictDraft(radiantHeroes, direHeroes)                // POST /draft/predict
recommendPicks({allyPicks, enemyPicks, bans, targetTeam, topN}) // POST /draft/recommend
analyzeCoachMatch(payload)                             // POST /coach/analyze
fetchPlayerProfile(accountId)                         // GET  /player/:id/profile
fetchHeroMatrix(heroId)                               // GET  /heroes/:id/matrix
evaluateRoster(playerIds)                             // POST /roster/compatibility
fetchMatchPlayers(matchId = -1)                       // GET  /match/:id/players
recommendItems(heroId, enemyHeroes)                   // POST /items/recommend
```

All functions have **try/catch with graceful fallback returns** — API failures do not crash the frontend.
When adding a new endpoint, add its Python route in `main.py` AND its JS function in `api.js`.

---

### Missing 8: Streamlit dashboard — 4-page structure

`src/dashboard/app.py` is a **4-page Streamlit app** with a sidebar selector:

| Page | Sidebar label | Features |
|---|---|---|
| 1 | 🗡️ Draft Room | Pick radiant/dire heroes → live XGBoost win probability + top N recommendations |
| 2 | 📊 Between-Match Coach | Enter hero + 10 stats → percentile radar + bottleneck detection + next-game action plan |
| 3 | 🔍 Player Profiler | Enter account_id → archetype radar + TrueSkill rating + 5-player roster compatibility |
| 4 | 🌐 Synergy & Counter Matrix | Select any hero → synergies / counters / victims / item timing benchmarks |

Run: `streamlit run src/dashboard/app.py --server.port 8501`

---

### Missing 9: Python dependencies

No `requirements.txt` exists in the project. Install with:

```bash
pip install xgboost fastapi "uvicorn[standard]" pandas numpy pyarrow scikit-learn streamlit httpx pydantic
```

Key versions that are known to work:
- `xgboost>=2.0`, `fastapi>=0.110`, `pandas>=2.0`, `numpy>=1.26`, `pydantic>=2.0`

---

## 💡 SECTION 4 — Rules Claude Must Follow in This Codebase

1. **Never hardcode paths.** Always `from src.data.config import FEATURES_DIR, RAW_DATA_DIR, MODELS_DIR`.

2. **Never re-train the model unless explicitly asked.** `DraftAdvisor.train()` overwrites `models/draft_xgb_model.pkl` and takes minutes. Use `advisor.load_model()` for inference.

3. **The fallback player profile is NOT real data.** If `matches_analyzed` is 3 (the hardcoded fallback hero pool size), the output is hash-seeded synthetic. Never cite it as empirical.

4. **Use `src.data.loaders` helpers**, not bare `pd.read_csv("players.csv")` — the helpers handle path resolution and chunked loading.

5. **To extend hero-specific item timings**, add `elif hero_id in [NEW_IDS]:` around line 300 in `coach_engine.py` `get_hero_matrix()`.

6. **To add a new API endpoint:** add the Python route to `src/api/main.py` AND add the corresponding JS async function to `frontend/src/services/api.js`.

7. **Run tests after any backend change:** `python tests/test_platform.py`

8. **Frontend base URL is in `api.js` line 1** (`const API_BASE = "http://localhost:8000"`). Change it there for any non-local deployment.

9. **`match_id=0` returns a random match**, not match 0 (0 is not in the dataset). Pass `-1` explicitly for random. Pass a real ID (e.g. `3901496438`) for a specific match.

10. **`data/processed/` and `configs/` are empty.** Don't waste time looking for files there.

---

## 📂 SECTION 5 — Complete Key Files Reference (19 files)

| File | Purpose |
|---|---|
| [`src/api/main.py`](file:///e:/Dota2/src/api/main.py) | FastAPI app — all 8 REST endpoints + Pydantic schemas |
| [`src/models/draft_advisor.py`](file:///e:/Dota2/src/models/draft_advisor.py) | Model 1 — XGBoost classifier: train(), load_model(), predict_win_probability(), recommend_picks() |
| [`src/models/coach_engine.py`](file:///e:/Dota2/src/models/coach_engine.py) | Model 3 — analyze_player_match(), get_hero_matrix(), hero-specific timing overrides |
| [`src/models/player_profiler.py`](file:///e:/Dota2/src/models/player_profiler.py) | Model 4 — get_player_full_profile(), profile_player_matches(), evaluate_roster_compatibility(), get_match_players() |
| [`src/models/item_advisor.py`](file:///e:/Dota2/src/models/item_advisor.py) | Model 5 — rule-based situational counter-item recommender, CORE_ITEM_TIMINGS |
| [`src/data/config.py`](file:///e:/Dota2/src/data/config.py) | **All path constants** — single source of truth for directory locations |
| [`src/data/loaders.py`](file:///e:/Dota2/src/data/loaders.py) | CSV loading helpers — load_matches(), load_players(), get_hero_dict(), get_item_dict(), etc. |
| [`src/data/features.py`](file:///e:/Dota2/src/data/features.py) | Feature engineering — hero ID maps, build_draft_feature_matrix(), synergy/counter computation |
| [`src/data/benchmarks.py`](file:///e:/Dota2/src/data/benchmarks.py) | Benchmark generator — run to regenerate hero_benchmarks.parquet from players.csv |
| [`src/dashboard/app.py`](file:///e:/Dota2/src/dashboard/app.py) | Streamlit 4-page dashboard (Draft Room, Coach, Profiler, Matrix Explorer) |
| [`frontend/src/App.jsx`](file:///e:/Dota2/frontend/src/App.jsx) | React root entry + tab-based routing |
| [`frontend/src/services/api.js`](file:///e:/Dota2/frontend/src/services/api.js) | **All frontend API calls** — add new endpoint functions here |
| [`frontend/src/components/DraftRoom.jsx`](file:///e:/Dota2/frontend/src/components/DraftRoom.jsx) | Draft picks, bans, XGBoost recommendations, counter items drawer |
| [`frontend/src/components/BetweenMatchCoach.jsx`](file:///e:/Dota2/frontend/src/components/BetweenMatchCoach.jsx) | Post-match stats form + coaching report + "Load Sample Match" button |
| [`frontend/src/components/PlayerScout.jsx`](file:///e:/Dota2/frontend/src/components/PlayerScout.jsx) | Player profile search, radar chart, roster compatibility analyzer |
| [`frontend/src/components/MatrixExplorer.jsx`](file:///e:/Dota2/frontend/src/components/MatrixExplorer.jsx) | Hero synergy/counter/victim matrix + item timing benchmarks UI |
| [`tests/test_platform.py`](file:///e:/Dota2/tests/test_platform.py) | 19-test suite — run with `python tests/test_platform.py` or `pytest tests/test_platform.py -v` |
| [`models/draft_xgb_model.pkl`](file:///e:/Dota2/models/draft_xgb_model.pkl) | Trained XGBoost model artifact (468 KB) |
| [`models/draft_model_meta.json`](file:///e:/Dota2/models/draft_model_meta.json) | Training metrics: AUC, accuracy, log loss, sample counts |
