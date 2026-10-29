"""
Between-Match Strategic Coach (Model 3):
Analyzes post-match player performance against 50k-match empirical benchmarks,
identifies tactical leaks, calculates percentile rankings, and generates
actionable, concrete coaching adjustments for the upcoming match.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
import pandas as pd

from src.data.config import FEATURES_DIR
from src.data.features import HERO_ID_TO_NAME

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class BetweenMatchCoach:
    def __init__(self):
        self.benchmarks: Dict[int, Dict[str, Any]] = {}
        self.counter_df: Optional[pd.DataFrame] = None
        self.synergy_df: Optional[pd.DataFrame] = None
        self._load_knowledge()

    def _load_knowledge(self):
        bench_path = FEATURES_DIR / "hero_benchmarks.parquet"
        counter_path = FEATURES_DIR / "hero_counter.parquet"
        synergy_path = FEATURES_DIR / "hero_synergy.parquet"

        if bench_path.exists():
            df = pd.read_parquet(bench_path)
            for _, r in df.iterrows():
                self.benchmarks[int(r["hero_id"])] = r.to_dict()

        if counter_path.exists():
            self.counter_df = pd.read_parquet(counter_path)

        if synergy_path.exists():
            self.synergy_df = pd.read_parquet(synergy_path)

    def _estimate_percentile(self, hero_id: int, metric: str, value: float) -> float:
        """
        Estimates the empirical percentile (0-100) of a metric value
        using precomputed p10, p25, p50, p75, p90 quantiles.
        """
        if hero_id not in self.benchmarks:
            return 50.0

        bm = self.benchmarks[hero_id]
        p10 = bm.get(f"{metric}_p10", 0)
        p25 = bm.get(f"{metric}_p25", 0)
        p50 = bm.get(f"{metric}_p50", 0)
        p75 = bm.get(f"{metric}_p75", 0)
        p90 = bm.get(f"{metric}_p90", 0)

        quantiles = [0.0, 10.0, 25.0, 50.0, 75.0, 90.0, 100.0]
        # For lower bound, assume 0 or half of p10; for upper bound, 1.25 * p90
        lower = max(0.0, p10 * 0.5)
        upper = p90 * 1.35 if p90 > 0 else 100.0
        points = [lower, p10, p25, p50, p75, p90, upper]

        # Monotonic check
        for i in range(1, len(points)):
            if points[i] <= points[i - 1]:
                points[i] = points[i - 1] + 0.001

        percentile = float(np.interp(value, points, quantiles))
        return round(float(np.clip(percentile, 1.0, 99.0)), 1)

    def analyze_player_match(
        self,
        hero_id: int,
        player_stats: Dict[str, float],
        opponent_heroes: Optional[List[int]] = None,
        won_match: bool = False,
    ) -> Dict[str, Any]:
        """
        Full Between-Match diagnostic:
        - Percentile evaluations across 6 gameplay pillars
        - Critical leaks / Bottlenecks
        - Opponent counter analysis
        - Ban & pick recommendations for the next match
        - Specific tactical action items
        """
        hero_name = HERO_ID_TO_NAME.get(hero_id, f"Hero {hero_id}")
        bm = self.benchmarks.get(hero_id, {})

        gpm = player_stats.get("gold_per_min", 450)
        xpm = player_stats.get("xp_per_min", 500)
        kills = player_stats.get("kills", 5)
        deaths = player_stats.get("deaths", 5)
        assists = player_stats.get("assists", 8)
        last_hits = player_stats.get("last_hits", 180)
        denies = player_stats.get("denies", 5)
        hero_damage = player_stats.get("hero_damage", 12000)
        tower_damage = player_stats.get("tower_damage", 1500)
        stuns = player_stats.get("stuns", 0.0)

        # 1. Percentiles
        gpm_pct = self._estimate_percentile(hero_id, "gold_per_min", gpm)
        xpm_pct = self._estimate_percentile(hero_id, "xp_per_min", xpm)
        hd_pct = self._estimate_percentile(hero_id, "hero_damage", hero_damage)
        td_pct = self._estimate_percentile(hero_id, "tower_damage", tower_damage)
        lh_pct = self._estimate_percentile(hero_id, "last_hits", last_hits)
        denies_pct = self._estimate_percentile(hero_id, "denies", denies)
        stuns_pct = self._estimate_percentile(hero_id, "stuns", stuns)

        # Survivability: lower deaths = higher percentile
        death_raw_pct = self._estimate_percentile(hero_id, "deaths", deaths)
        survivability_pct = round(100.0 - death_raw_pct, 1)

        # 2. Performance Pillars Radar Scores (0 to 100)
        pillars = {
            "Farming Tempo": round((gpm_pct + lh_pct) / 2, 1),
            "Teamfight Impact": round((hd_pct + (assists / (deaths + 1) * 10)) / 2, 1),
            "Objective Focus": td_pct,
            "Laning Precision": denies_pct,
            "Crowd Control": stuns_pct,
            "Survivability": survivability_pct,
        }

        # 3. Detect Critical Leaks / Bottlenecks
        bottlenecks = []
        if gpm_pct < 35.0:
            avg_gpm = bm.get("gold_per_min_p50", 500)
            bottlenecks.append({
                "category": "Farming Deficit",
                "severity": "HIGH",
                "observation": f"Your GPM ({gpm:.0f}) is at the {gpm_pct:.0f}th percentile (Median: {avg_gpm:.0f}).",
                "action": "Prioritize lane pushing and stacking adjacent jungle camps between waves to avoid dead farming time.",
            })

        if deaths > bm.get("deaths_p75", 7.0):
            bottlenecks.append({
                "category": "High Mortality Rate",
                "severity": "HIGH",
                "observation": f"You died {deaths} times (Top {death_raw_pct:.0f}% most deaths on {hero_name}).",
                "action": "Avoid over-extending without vision. Buy defensive positioning items (Force Staff/Blink/BKB) earlier.",
            })

        if tower_damage < bm.get("tower_damage_p25", 800) and gpm_pct > 40.0:
            bottlenecks.append({
                "category": "Low Objective Conversion",
                "severity": "MEDIUM",
                "observation": f"Tower damage was only {tower_damage:.0f} despite decent farm.",
                "action": "After winning a teamfight, immediately rotate to siege the nearest tower rather than falling back to jungle.",
            })

        if denies < bm.get("denies_p25", 3) and hero_id not in [14, 86, 26]:  # Exclude roaming/supports
            bottlenecks.append({
                "category": "Weak Lane Control",
                "severity": "LOW",
                "observation": f"Only {denies} denies in the match.",
                "action": "Work on creep equilibrium control; pull the lane and deny ranged creeps to starve the opposing offlaner.",
            })

        # 4. Tactical Opponent Counter & Draft Analysis for Next Match
        opponent_counters = []
        suggested_bans = []
        alternative_picks = []

        if opponent_heroes and self.counter_df is not None:
            for opp_id in opponent_heroes:
                opp_name = HERO_ID_TO_NAME.get(opp_id, f"Hero {opp_id}")
                matchup = self.counter_df[
                    (self.counter_df["hero"] == opp_id) & (self.counter_df["opponent"] == hero_id)
                ]
                if not matchup.empty:
                    adv = float(matchup.iloc[0]["advantage"])
                    wr = float(matchup.iloc[0]["win_rate"])
                    if adv > 0.02:
                        opponent_counters.append({
                            "enemy_hero": opp_name,
                            "enemy_advantage": round(adv * 100, 1),
                            "enemy_win_rate_vs_you": round(wr * 100, 1),
                        })
                        suggested_bans.append(opp_name)

            # Recommend alternative heroes that counter the opponent's heaviest threats
            if opponent_counters:
                worst_opp = max(opponent_counters, key=lambda x: x["enemy_advantage"])
                opp_hero_id = [k for k, v in HERO_ID_TO_NAME.items() if v == worst_opp["enemy_hero"]]
                if opp_hero_id:
                    countering = self.counter_df[
                        (self.counter_df["opponent"] == opp_hero_id[0]) & (self.counter_df["advantage"] > 0.04)
                    ].sort_values("advantage", ascending=False).head(3)
                    for _, row in countering.iterrows():
                        alternative_picks.append({
                            "hero_name": row["hero_name"],
                            "counter_advantage": round(row["advantage"] * 100, 1),
                            "reason": f"Strong counter to {worst_opp['enemy_hero']} (+{row['advantage']*100:.1f}%)",
                        })

        # 5. Immediate Action Plan for Next Game
        action_plan = []
        if not won_match:
            action_plan.append(f"Reset mental focus: Review why lane momentum was lost.")
        if suggested_bans:
            action_plan.append(f"Draft Ban Priority: Ban {', '.join(suggested_bans[:2])} to protect your core pool.")
        if bottlenecks:
            action_plan.append(f"In-Game Execution: {bottlenecks[0]['action']}")
        if alternative_picks:
            alt_names = [a['hero_name'] for a in alternative_picks[:2]]
            action_plan.append(f"Pocket Pick Option: If enemy re-picks their comfort, draft {', '.join(alt_names)}.")

        return {
            "hero_name": hero_name,
            "match_result": "VICTORY" if won_match else "DEFEAT",
            "percentiles": {
                "gold_per_min": gpm_pct,
                "xp_per_min": xpm_pct,
                "hero_damage": hd_pct,
                "tower_damage": td_pct,
                "last_hits": lh_pct,
                "denies": denies_pct,
                "stuns": stuns_pct,
                "survivability": survivability_pct,
            },
            "pillars": pillars,
            "critical_bottlenecks": bottlenecks,
            "opponent_threat_analysis": opponent_counters,
            "next_match_bans": list(set(suggested_bans)),
            "alternative_counter_picks": alternative_picks,
            "coach_action_plan": action_plan,
        }

    def get_hero_matrix(self, hero_id: int) -> Dict[str, Any]:
        """
        Returns precomputed top 5 allied synergies, top 5 hardest counters,
        top 5 victims countered by this hero, and key item timing benchmarks.
        """
        hero_name = HERO_ID_TO_NAME.get(hero_id, f"Hero {hero_id}")
        synergies = []
        counters = []
        victims = []

        if self.synergy_df is not None:
            syn_subset = self.synergy_df[
                (self.synergy_df["hero_1"] == hero_id) | (self.synergy_df["hero_2"] == hero_id)
            ].copy()
            if not syn_subset.empty:
                syn_subset["partner"] = syn_subset.apply(
                    lambda r: r["hero_2_name"] if r["hero_1"] == hero_id else r["hero_1_name"], axis=1
                )
                top_syn = syn_subset.sort_values("synergy_score", ascending=False).head(5)
                for _, row in top_syn.iterrows():
                    synergies.append({
                        "partner": str(row["partner"]),
                        "games": int(row["games"]),
                        "winRate": round(float(row["win_rate"]) * 100, 1),
                        "delta": f"{float(row['synergy_score']) * 100:+.1f}%",
                    })

        if self.counter_df is not None:
            # 1. Hardest counters (who beats this hero the most)
            threats_df = self.counter_df[self.counter_df["opponent"] == hero_id].sort_values("advantage", ascending=False).head(5)
            for _, row in threats_df.iterrows():
                counters.append({
                    "threat": str(row["hero_name"]),
                    "games": int(row["games"]),
                    "threatWinRate": round(float(row["win_rate"]) * 100, 1),
                    "disadvantage": f"{-float(row['advantage']) * 100:+.1f}%",
                })

            # 2. Victims countered by this hero (who this hero beats)
            victims_df = self.counter_df[self.counter_df["hero"] == hero_id].sort_values("advantage", ascending=False).head(5)
            for _, row in victims_df.iterrows():
                victims.append({
                    "victim": str(row["opponent_name"]),
                    "games": int(row["games"]),
                    "myWinRate": round(float(row["win_rate"]) * 100, 1),
                    "advantage": f"{float(row['advantage']) * 100:+.1f}%",
                })

        # Core item timing benchmarks
        timings = [
            {"item": "Blink Dagger / Manta Style", "targetMin": "14 - 18 min", "priority": "Initiation & Power Spike"},
            {"item": "Black King Bar", "targetMin": "19 - 23 min", "priority": "Spell Immunity & Teamfight"},
            {"item": "Aghanim's Scepter / Shard", "targetMin": "20 - 25 min", "priority": "Hero Ability Augment"},
            {"item": "Shiva's Guard / Assault Cuirass", "targetMin": "28 - 32 min", "priority": "Late Game Control & Armor"},
        ]
        if hero_id == 1:  # Anti-Mage
            timings = [
                {"item": "Battle Fury", "targetMin": "13 - 15 min", "priority": "Core Farming Engine"},
                {"item": "Manta Style", "targetMin": "20 - 22 min", "priority": "Dispel & Pickoff Spike"},
                {"item": "Basher / Abyssal", "targetMin": "26 - 28 min", "priority": "Lockdown Burst"},
                {"item": "Black King Bar", "targetMin": "Situational", "priority": "Against Heavy Disables"},
            ]
        elif hero_id in [8, 44]:  # Juggernaut, PA
            timings = [
                {"item": "Phase Boots / Maelstrom or Deso", "targetMin": "12 - 15 min", "priority": "Early Lane & Kill Pressure"},
                {"item": "Manta Style / BKB", "targetMin": "20 - 22 min", "priority": "Teamfight Survival Spike"},
                {"item": "Eye of Skadi / Basher", "targetMin": "26 - 30 min", "priority": "Core Lockdown & Scaling"},
                {"item": "Satanic / Butterfly", "targetMin": "32 - 36 min", "priority": "Late Game Sustain"},
            ]
        elif hero_id == 74:  # Invoker
            timings = [
                {"item": "Hand of Midas", "targetMin": "9 - 11 min", "priority": "XP & Level Progression"},
                {"item": "Aghanim's Scepter", "targetMin": "18 - 21 min", "priority": "Spell Cooldown & Mana Pool"},
                {"item": "Black King Bar", "targetMin": "23 - 26 min", "priority": "Teamfight Spell Casting"},
                {"item": "Refresher Orb / Octarine", "targetMin": "30 - 34 min", "priority": "Cataclysm Double Combo"},
            ]
        elif hero_id == 2:  # Axe
            timings = [
                {"item": "Blink Dagger", "targetMin": "12 - 14 min", "priority": "Berserker's Call Initiation"},
                {"item": "Blade Mail", "targetMin": "16 - 18 min", "priority": "Physical Damage Reflection"},
                {"item": "Black King Bar", "targetMin": "22 - 25 min", "priority": "CC Immunity on Initiation"},
                {"item": "Heart of Tarrasque", "targetMin": "28 - 32 min", "priority": "Frontline Bulk & Regen"},
            ]
        elif hero_id == 14:  # Pudge
            timings = [
                {"item": "Tranquil Boots & Urn", "targetMin": "8 - 11 min", "priority": "Roaming & Kill Sustain"},
                {"item": "Blink Dagger / Aether Lens", "targetMin": "14 - 17 min", "priority": "Dismember Initiation & Hook Range"},
                {"item": "Aghanim's Scepter", "targetMin": "22 - 26 min", "priority": "Rot Area & Lifesteal Spike"},
                {"item": "Heart of Tarrasque", "targetMin": "28 - 32 min", "priority": "Flesh Heap Scaling Bulk"},
            ]
        elif hero_id == 5:  # Crystal Maiden
            timings = [
                {"item": "Tranquil Boots & Glimmer Cape", "targetMin": "12 - 15 min", "priority": "Freezing Field Invisibility"},
                {"item": "Force Staff / Blink Dagger", "targetMin": "18 - 22 min", "priority": "Kiting & Positioning"},
                {"item": "Black King Bar / Ghost Scepter", "targetMin": "24 - 28 min", "priority": "Channeling Protection"},
                {"item": "Aghanim's Shard", "targetMin": "15 min", "priority": "Mobile Freezing Field Frostbite"},
            ]
        elif hero_id == 18:  # Sven
            timings = [
                {"item": "Mask of Madness / Echo Sabre", "targetMin": "11 - 14 min", "priority": "Cleave Farming Engine"},
                {"item": "Black King Bar", "targetMin": "18 - 21 min", "priority": "God's Strength Unstoppable Burst"},
                {"item": "Blink Dagger", "targetMin": "22 - 24 min", "priority": "Storm Hammer Gap-Close"},
                {"item": "Daedalus / Bloodthorn", "targetMin": "27 - 30 min", "priority": "One-Shot Critical Cleave"},
            ]
        elif hero_id == 17:  # Storm Spirit
            timings = [
                {"item": "Kaya / Orchid Malevolence", "targetMin": "13 - 16 min", "priority": "Mana Efficiency & Pickoff Silence"},
                {"item": "Black King Bar", "targetMin": "20 - 23 min", "priority": "Zip-In Teamfight Immunity"},
                {"item": "Bloodstone / Shiva's Guard", "targetMin": "25 - 29 min", "priority": "Spell Lifesteal & Mana Pool"},
                {"item": "Scythe of Vyse", "targetMin": "31 - 35 min", "priority": "Instant Hex Lockdown"},
            ]

        return {
            "hero_id": hero_id,
            "hero_name": hero_name,
            "synergies": synergies,
            "counters": counters,
            "victims": victims,
            "timings": timings,
        }


if __name__ == "__main__":
    coach = BetweenMatchCoach()
    sample_stats = {
        "gold_per_min": 410,
        "xp_per_min": 480,
        "kills": 3,
        "deaths": 9,
        "assists": 6,
        "last_hits": 190,
        "denies": 2,
        "hero_damage": 9500,
        "tower_damage": 420,
        "stuns": 0.0,
    }
    # Player played Anti-Mage (hero_id 1) against Axe (2) and Bloodseeker (4)
    report = coach.analyze_player_match(
        hero_id=1,
        player_stats=sample_stats,
        opponent_heroes=[2, 4],
        won_match=False,
    )
    print("\n--- COACH POST-MATCH REPORT ---")
    print(f"Hero: {report['hero_name']} | Result: {report['match_result']}")
    print("Pillars:", report["pillars"])
    print("\nCritical Bottlenecks:")
    for b in report["critical_bottlenecks"]:
        print(f" - [{b['severity']}] {b['category']}: {b['observation']}")
        print(f"   -> {b['action']}")
    print("\nNext Match Action Plan:")
    for a in report["coach_action_plan"]:
        print(f" * {a}")
