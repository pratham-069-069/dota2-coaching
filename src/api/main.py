"""
FastAPI REST API for Dota 2 Coaching Intelligence Platform.
Exposes endpoints for:
- Hero Draft Recommendations & Win Probability
- Between-Match Post-Match Diagnostics & Tactical Suggestions
- Player Profiling & TrueSkill Ratings
- Situational Itemization Guidance
"""

import logging
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.models.draft_advisor import DraftAdvisor
from src.models.coach_engine import BetweenMatchCoach
from src.models.player_profiler import PlayerProfiler
from src.models.item_advisor import ItemAdvisor
from src.models.live_simulator import LiveGameSimulator
from src.data.features import HERO_ID_TO_NAME, ALL_HERO_IDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dota 2 Coaching Intelligence API",
    description="ML-powered strategic drafting and between-match coaching engine for pro players and coaches.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize models
draft_advisor = DraftAdvisor()
coach_engine = BetweenMatchCoach()
player_profiler = PlayerProfiler()
item_advisor = ItemAdvisor()
live_simulator = LiveGameSimulator(draft_advisor)


# --- Pydantic Schemas ---

class DraftPredictRequest(BaseModel):
    radiant_heroes: List[int] = Field(..., description="List of 1 to 5 hero IDs on Radiant")
    dire_heroes: List[int] = Field(..., description="List of 1 to 5 hero IDs on Dire")

class DraftRecommendRequest(BaseModel):
    ally_picks: List[int] = Field(default=[], description="List of picked ally hero IDs")
    enemy_picks: List[int] = Field(default=[], description="List of picked enemy hero IDs")
    bans: Optional[List[int]] = Field(default=[], description="List of banned hero IDs")
    target_team: str = Field(default="radiant", description="'radiant' or 'dire'")
    top_n: int = Field(default=5, ge=1, le=20, description="Number of recommendations to return")

class CoachAnalyzeRequest(BaseModel):
    hero_id: int = Field(..., description="Hero played in the match")
    won_match: bool = Field(default=False, description="Whether the match was won")
    player_stats: Dict[str, float] = Field(
        ...,
        description="Match stats: gold_per_min, xp_per_min, kills, deaths, assists, last_hits, denies, hero_damage, tower_damage, stuns"
    )
    opponent_heroes: Optional[List[int]] = Field(default=[], description="Opponent hero IDs")

class ItemRecommendRequest(BaseModel):
    hero_id: int = Field(..., description="Target hero ID")
    enemy_heroes: List[int] = Field(..., description="Enemy hero IDs")

class RosterCompatibilityRequest(BaseModel):
    player_ids: Optional[List[int]] = Field(default=[], description="List of 2-5 player account IDs")
    player_profiles: Optional[List[Dict[str, Any]]] = Field(default=[], description="List of pre-resolved player profile dictionaries")

class SimLiveEvent(BaseModel):
    minute: int = Field(..., description="Game minute when the event occurs")
    team: str = Field(..., description="'radiant' or 'dire'", pattern="^(radiant|dire)$")
    type: str = Field(..., description="Event type: first_blood, kill, teamfight, roshan, tower, ward_sweep")
    count: int = Field(default=1, ge=1, le=5, description="Multi-kill count for kill/teamfight events")

class SimLiveRequest(BaseModel):
    radiant_heroes: List[int] = Field(default=[], description="Radiant hero IDs")
    dire_heroes: List[int] = Field(default=[], description="Dire hero IDs")
    minute: int = Field(default=0, ge=0, le=60, description="Current game clock in minutes")
    seed: int = Field(default=0, description="Timeline seed (same seed = same base game)")
    extra_events: List[SimLiveEvent] = Field(default=[], description="User-injected what-if events")
    include_projection: bool = Field(default=True, description="Include AI forward projection to 60 min")


# --- Endpoints ---

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "models": {
            "draft_advisor_loaded": draft_advisor.model is not None or draft_advisor.load_model(),
            "hero_benchmarks_loaded": len(coach_engine.benchmarks) > 0,
            "player_profiler_loaded": player_profiler.ratings_df is not None,
            "player_matches_loaded": player_profiler.matches_df is not None,
        }
    }

@app.get("/heroes")
def get_all_heroes():
    """Returns list of all available heroes with ID and name."""
    heroes = []
    for hid in ALL_HERO_IDS:
        int_hid = int(hid)
        stats = draft_advisor.hero_stats.get(int_hid, {})
        heroes.append({
            "hero_id": int_hid,
            "name": str(HERO_ID_TO_NAME.get(int_hid, f"Hero {int_hid}")),
            "win_rate": float(stats.get("win_rate", 0.5)),
            "pick_rate": float(stats.get("pick_rate", 0.05)),
        })
    return {"count": len(heroes), "heroes": heroes}

@app.get("/heroes/{hero_id}/matrix")
def get_hero_matrix_endpoint(hero_id: int):
    """Fetches top 5 synergies, top 5 counters, top 5 victims, and timing benchmarks for any hero."""
    try:
        matrix = coach_engine.get_hero_matrix(hero_id)
        return matrix
    except Exception as e:
        logger.error(f"Matrix fetch error for hero {hero_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/draft/predict")
def predict_draft_win_rate(req: DraftPredictRequest):
    """Predicts Radiant and Dire win probabilities given current picks."""
    try:
        result = draft_advisor.predict_win_probability(req.radiant_heroes, req.dire_heroes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/draft/recommend")
def recommend_hero_picks(req: DraftRecommendRequest):
    """Recommends optimal hero picks considering synergy and counter advantages."""
    try:
        recs = draft_advisor.recommend_picks(
            ally_picks=req.ally_picks,
            enemy_picks=req.enemy_picks,
            bans=req.bans,
            target_team=req.target_team,
            top_n=req.top_n,
        )
        return {
            "target_team": req.target_team,
            "recommendations": recs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/coach/analyze")
def post_match_coaching_report(req: CoachAnalyzeRequest):
    """Generates post-match diagnostic report with percentile scores and next-game tactical adjustments."""
    try:
        report = coach_engine.analyze_player_match(
            hero_id=req.hero_id,
            player_stats=req.player_stats,
            opponent_heroes=req.opponent_heroes,
            won_match=req.won_match,
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/player/{account_id}/profile")
def get_player_profile(account_id: int):
    """Fetches career TrueSkill rating, playstyle archetype, radar traits, and comfort heroes for an account_id."""
    return player_profiler.get_player_full_profile(account_id)

@app.post("/roster/compatibility")
def analyze_roster_compatibility(req: RosterCompatibilityRequest):
    """Evaluates team synergy across 2-5 players, detecting greedy core conflicts and utility gaps."""
    items = req.player_ids if req.player_ids else req.player_profiles
    if not items:
        raise HTTPException(status_code=400, detail="Provide either player_ids or player_profiles")
    return player_profiler.evaluate_roster_compatibility(items)

@app.get("/match/{match_id}/players")
def get_match_players_endpoint(match_id: int):
    """Fetches all 10 players and their performance metrics from a given match (or random if match_id < 0)."""
    return player_profiler.get_match_players(match_id)

@app.post("/items/recommend")
def recommend_situational_items(req: ItemRecommendRequest):
    """Recommends counter items and timing milestones based on opponent lineup threats."""
    items = item_advisor.recommend_situational_items(req.hero_id, req.enemy_heroes)
    benchmarks = item_advisor.get_timing_benchmarks()
    return {
        "hero_name": HERO_ID_TO_NAME.get(req.hero_id, f"Hero {req.hero_id}"),
        "situational_counters": items,
        "core_timings": benchmarks,
    }
