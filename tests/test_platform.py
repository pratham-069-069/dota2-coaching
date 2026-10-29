"""
Comprehensive Integration & Unit Test Suite for Dota 2 Coaching Intelligence Platform.
Validates:
- 1. Draft Advisor ML predictions and pick recommendations with bans.
- 2. Empirical benchmark quantile evaluations and coach diagnostics.
- 3. Player profiling, playstyle archetypes, and roster compatibility analysis.
- 4. Synergy and counter matrix queries for all heroes.
- 5. Situational counter-itemization recommendations.
- 6. Full FastAPI REST API suite.
"""

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import pytest
    fixture = pytest.fixture
except ImportError:
    fixture = lambda *args, **kwargs: (lambda f: f)

from fastapi.testclient import TestClient

from src.models.draft_advisor import DraftAdvisor
from src.models.coach_engine import BetweenMatchCoach
from src.models.player_profiler import PlayerProfiler
from src.models.item_advisor import ItemAdvisor
from src.api.main import app


@fixture(scope="module")
def api_client():
    return TestClient(app)


@fixture(scope="module")
def draft_advisor():
    advisor = DraftAdvisor()
    advisor.load_model()
    return advisor


@fixture(scope="module")
def coach_engine():
    return BetweenMatchCoach()


@fixture(scope="module")
def player_profiler():
    return PlayerProfiler()


@fixture(scope="module")
def item_advisor():
    return ItemAdvisor()


# --- 1. Draft Advisor Tests ---

def test_draft_advisor_prediction(draft_advisor):
    # Radiant: Anti-Mage (1), CM (5); Dire: Juggernaut (8), Pudge (14)
    pred = draft_advisor.predict_win_probability([1, 5], [8, 14])
    assert "radiant_win_prob" in pred
    assert "dire_win_prob" in pred
    assert round(pred["radiant_win_prob"] + pred["dire_win_prob"], 2) == 1.0
    assert 0.0 < pred["radiant_win_prob"] < 1.0


def test_draft_advisor_recommendations_with_bans(draft_advisor):
    # Exclude Invoker (74) via bans
    recs = draft_advisor.recommend_picks(
        ally_picks=[1],
        enemy_picks=[2],
        bans=[74],
        target_team="radiant",
        top_n=5,
    )
    assert len(recs) == 5
    recommended_ids = [r["hero_id"] for r in recs]
    assert 74 not in recommended_ids
    assert 1 not in recommended_ids
    assert 2 not in recommended_ids
    for r in recs:
        assert "projected_win_prob" in r
        assert "win_prob_gain" in r
        assert len(r["reasons"]) > 0


# --- 2. Between-Match Coach Tests ---

def test_coach_analyze_player_match(coach_engine):
    sample_stats = {
        "gold_per_min": 380,
        "xp_per_min": 420,
        "kills": 2,
        "deaths": 9,
        "assists": 4,
        "last_hits": 160,
        "denies": 1,
        "hero_damage": 8000,
        "tower_damage": 300,
        "stuns": 0.0,
    }
    report = coach_engine.analyze_player_match(
        hero_id=1,  # Anti-Mage
        player_stats=sample_stats,
        opponent_heroes=[2, 4],  # Axe, Bloodseeker
        won_match=False,
    )
    assert report["hero_name"] == "Anti-Mage"
    assert report["match_result"] == "DEFEAT"
    assert "pillars" in report
    assert len(report["pillars"]) == 6
    assert "Farming Tempo" in report["pillars"]
    assert "Survivability" in report["pillars"]
    assert len(report["critical_bottlenecks"]) > 0
    assert len(report["coach_action_plan"]) > 0


def test_coach_hero_matrix(coach_engine):
    matrix = coach_engine.get_hero_matrix(1)  # Anti-Mage
    assert matrix["hero_id"] == 1
    assert matrix["hero_name"] == "Anti-Mage"
    assert len(matrix["synergies"]) > 0
    assert len(matrix["counters"]) > 0
    assert len(matrix["victims"]) > 0
    assert len(matrix["timings"]) > 0


def test_extended_hero_timings(coach_engine):
    # Test Invoker (74), Axe (2), and Crystal Maiden (5) timings
    invoker_matrix = coach_engine.get_hero_matrix(74)
    assert any("Hand of Midas" in t["item"] for t in invoker_matrix["timings"])
    axe_matrix = coach_engine.get_hero_matrix(2)
    assert any("Blink Dagger" in t["item"] for t in axe_matrix["timings"])
    cm_matrix = coach_engine.get_hero_matrix(5)
    assert any("Glimmer Cape" in t["item"] for t in cm_matrix["timings"])


# --- 3. Player Profiler & Scouting Tests ---

def test_player_trueskill_rating(player_profiler):
    rating = player_profiler.get_player_rating(236579)
    assert rating["account_id"] == 236579
    assert rating["total_matches"] > 0
    assert rating["trueskill_mu"] > 0
    assert rating["estimated_skill_rating"] > 500


def test_player_full_profile(player_profiler):
    # Account 2701 is in the 50k match records
    prof = player_profiler.get_player_full_profile(2701)
    assert prof["account_id"] == 2701
    assert "archetype" in prof
    assert "radar_scores" in prof
    assert len(prof["radar_scores"]) == 6
    assert len(prof["top_comfort_heroes"]) > 0


def test_roster_compatibility_evaluation(player_profiler):
    # Evaluate 3 players
    roster_res = player_profiler.evaluate_roster_compatibility([2701, 10307, 18680])
    assert "roster_synergy_score" in roster_res
    assert 0 <= roster_res["roster_synergy_score"] <= 100
    assert "resource_conflict_detected" in roster_res
    assert "utility_coverage" in roster_res
    assert len(roster_res["coach_notes"]) > 0
    assert len(roster_res["players"]) == 3


def test_get_match_players(player_profiler):
    match_data = player_profiler.get_match_players(0)
    assert match_data["match_id"] == 0
    assert match_data["player_count"] == 10
    assert len(match_data["players"]) == 10


# --- 4. Situational Item Advisor Tests ---

def test_item_advisor_recommendations(item_advisor):
    # Phantom Assassin (44) and Lion (26) on enemy team
    recs = item_advisor.recommend_situational_items(hero_id=1, enemy_hero_ids=[44, 26])
    assert len(recs) > 0
    item_names = [r["item_name"] for r in recs]
    assert any("Monkey King Bar" in name or "Bloodthorn" in name for name in item_names)
    assert any("Black King Bar" in name or "Lotus" in name for name in item_names)


def test_extended_situational_item_counters(item_advisor):
    # Test healing threat (Necrophos: 36) and illusion threat (Phantom Lancer: 12)
    recs = item_advisor.recommend_situational_items(hero_id=1, enemy_hero_ids=[36, 12])
    assert len(recs) > 0
    item_names = [r["item_name"] for r in recs]
    assert any("Spirit Vessel" in name or "Skadi" in name for name in item_names)
    assert any("Mjollnir" in name or "Battle Fury" in name or "Radiance" in name for name in item_names)


# --- 5. FastAPI Endpoints Tests ---

def test_api_health(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["models"]["draft_advisor_loaded"] is True
    assert data["models"]["hero_benchmarks_loaded"] is True


def test_api_heroes(api_client):
    res = api_client.get("/heroes")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 100
    assert len(data["heroes"]) > 100


def test_api_hero_matrix(api_client):
    res = api_client.get("/heroes/1/matrix")
    assert res.status_code == 200
    data = res.json()
    assert data["hero_name"] == "Anti-Mage"
    assert len(data["synergies"]) == 5
    assert len(data["counters"]) == 5
    assert len(data["victims"]) == 5


def test_api_draft_predict(api_client):
    res = api_client.post("/draft/predict", json={
        "radiant_heroes": [1, 5],
        "dire_heroes": [8, 14],
    })
    assert res.status_code == 200
    data = res.json()
    assert "radiant_win_prob" in data
    assert "dire_win_prob" in data


def test_api_draft_recommend(api_client):
    res = api_client.post("/draft/recommend", json={
        "ally_picks": [1],
        "enemy_picks": [8],
        "bans": [74],
        "target_team": "radiant",
        "top_n": 5,
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["recommendations"]) == 5


def test_api_coach_analyze(api_client):
    res = api_client.post("/coach/analyze", json={
        "hero_id": 1,
        "won_match": False,
        "player_stats": {
            "gold_per_min": 420,
            "xp_per_min": 480,
            "kills": 3,
            "deaths": 8,
            "assists": 5,
            "last_hits": 195,
            "denies": 3,
            "hero_damage": 9200,
            "tower_damage": 450,
            "stuns": 0.0,
        },
        "opponent_heroes": [2, 4],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["hero_name"] == "Anti-Mage"
    assert "pillars" in data


def test_api_player_profile(api_client):
    res = api_client.get("/player/2701/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["account_id"] == 2701
    assert "archetype" in data
    assert "radar_scores" in data


def test_api_roster_compatibility(api_client):
    res = api_client.post("/roster/compatibility", json={
        "player_ids": [2701, 10307, 18680],
    })
    assert res.status_code == 200
    data = res.json()
    assert "roster_synergy_score" in data


def test_api_match_players(api_client):
    res = api_client.get("/match/0/players")
    assert res.status_code == 200
    data = res.json()
    assert data["player_count"] == 10


def test_api_items_recommend(api_client):
    res = api_client.post("/items/recommend", json={
        "hero_id": 1,
        "enemy_heroes": [44, 26],
    })
    assert res.status_code == 200
    data = res.json()
    assert len(data["situational_counters"]) > 0


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING DOTA 2 PLATFORM AUTOMATED TEST SUITE")
    print("=" * 60)

    client = TestClient(app)
    advisor = DraftAdvisor()
    advisor.load_model()
    coach = BetweenMatchCoach()
    profiler = PlayerProfiler()
    item_adv = ItemAdvisor()

    tests = [
        ("Draft Advisor: Win Probability Prediction", lambda: test_draft_advisor_prediction(advisor)),
        ("Draft Advisor: Pick Recommendation with Bans", lambda: test_draft_advisor_recommendations_with_bans(advisor)),
        ("Coach Engine: Performance Diagnostics & Leaks", lambda: test_coach_analyze_player_match(coach)),
        ("Coach Engine: Hero Matrix Analytics", lambda: test_coach_hero_matrix(coach)),
        ("Coach Engine: Extended Hero Timing Overrides", lambda: test_extended_hero_timings(coach)),
        ("Player Profiler: TrueSkill Rating Index", lambda: test_player_trueskill_rating(profiler)),
        ("Player Profiler: Full Archetype Fingerprint", lambda: test_player_full_profile(profiler)),
        ("Player Profiler: Roster Compatibility Analyzer", lambda: test_roster_compatibility_evaluation(profiler)),
        ("Player Profiler: Match Ingestion Extraction", lambda: test_get_match_players(profiler)),
        ("Item Advisor: Situational Threats & Counters", lambda: test_item_advisor_recommendations(item_adv)),
        ("Item Advisor: Extended Regen & Illusion Counters", lambda: test_extended_situational_item_counters(item_adv)),
        ("REST API: Health Endpoint", lambda: test_api_health(client)),
        ("REST API: Heroes Catalog Endpoint", lambda: test_api_heroes(client)),
        ("REST API: Hero Matrix Explorer Endpoint", lambda: test_api_hero_matrix(client)),
        ("REST API: Draft Win Probability Endpoint", lambda: test_api_draft_predict(client)),
        ("REST API: Draft Recommendations Endpoint", lambda: test_api_draft_recommend(client)),
        ("REST API: Post-Match Coach Audit Endpoint", lambda: test_api_coach_analyze(client)),
        ("REST API: Full Player Scouting Profile Endpoint", lambda: test_api_player_profile(client)),
        ("REST API: 5-Player Roster Compatibility Endpoint", lambda: test_api_roster_compatibility(client)),
        ("REST API: Match Ingestion Endpoint", lambda: test_api_match_players(client)),
        ("REST API: Situational Counter Items Endpoint", lambda: test_api_items_recommend(client)),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {name} -> {e}")
            failed += 1

    print("=" * 60)
    print(f"TEST SUITE COMPLETE: {passed} PASSED, {failed} FAILED.")
    print("=" * 60)
    if failed > 0:
        exit(1)
